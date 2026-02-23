# -*- coding: utf-8 -*-
"""
DAG模板系统 - 预定义工作流程模板

基于三段式架构（LLM选择 + 程序执行 + LLM综合）的DAG模板管理系统。
提供5-8个典型的健身场景DAG模板，供LLM决策引擎选择。

核心特性：
1. 预定义DAG模板库
2. 模板验证和完整性检查
3. 模板选择和加载
4. 依赖关系管理

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-12
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
import json

logger = logging.getLogger(__name__)


class TemplateCategory(Enum):
    """模板类别"""
    TRAINING = "training"           # 训练相关
    NUTRITION = "nutrition"         # 营养相关
    SAFETY = "safety"              # 安全评估
    COMPREHENSIVE = "comprehensive" # 综合方案
    QUICK = "quick"                # 快速咨询


@dataclass
class DAGTemplate:
    """DAG模板定义"""
    template_id: str
    name: str
    description: str
    category: TemplateCategory
    applicable_intents: List[str]
    required_tools: List[str]
    optional_tools: List[str] = field(default_factory=list)
    tool_dependencies: Dict[str, List[str]] = field(default_factory=dict)
    parallel_groups: List[List[str]] = field(default_factory=list)
    expected_output: Dict[str, str] = field(default_factory=dict)
    safety_constraints: List[str] = field(default_factory=list)
    estimated_duration_seconds: float = 10.0
    complexity_level: int = 1  # 1-3: 简单、中等、复杂
    success_rate: float = 0.95
    response_hint: str = ""  # LLM响应提示：指导步骤10如何生成回答
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        data['category'] = self.category.value
        return data
    
    def validate(self) -> bool:
        """验证模板完整性"""
        # 检查必需字段
        if not self.template_id or not self.name:
            logger.error(f"模板缺少必需字段: template_id或name")
            return False
        
        # 检查工具列表（greeting模板允许为空）
        if not self.required_tools and self.template_id != "greeting":
            logger.error(f"模板 {self.template_id} 缺少必需工具")
            return False
        
        # 检查依赖关系中的工具是否在工具列表中
        all_tools = set(self.required_tools + self.optional_tools)
        for tool, deps in self.tool_dependencies.items():
            if tool not in all_tools:
                logger.error(f"模板 {self.template_id} 依赖关系中的工具 {tool} 不在工具列表中")
                return False
            for dep in deps:
                if dep not in all_tools:
                    logger.error(f"模板 {self.template_id} 工具 {tool} 的依赖 {dep} 不在工具列表中")
                    return False
        
        # 检查并行组中的工具是否在工具列表中
        for group in self.parallel_groups:
            for tool in group:
                if tool not in all_tools:
                    logger.error(f"模板 {self.template_id} 并行组中的工具 {tool} 不在工具列表中")
                    return False
        
        return True


class DAGTemplateManager:
    """DAG模板管理器"""
    
    def __init__(self):
        self.templates: Dict[str, DAGTemplate] = {}
        self._initialize_templates()
        self._validate_all_templates()
    
    def _initialize_templates(self):
        """初始化所有DAG模板"""
        
        # 模板0: 问候闲聊
        self.templates["greeting"] = DAGTemplate(
            template_id="greeting",
            name="问候闲聊",
            description="友好回应用户的问候和简单闲聊",
            category=TemplateCategory.QUICK,
            applicable_intents=[
                "你好",
                "早上好",
                "晚上好",
                "hi",
                "hello",
                "嗨",
                "在吗",
                "闲聊",
                "问候"
            ],
            required_tools=[],  # 不需要调用任何工具
            optional_tools=[],
            tool_dependencies={},
            parallel_groups=[],
            expected_output={
                "greeting_response": "简短友好的问候回应"
            },
            safety_constraints=[],
            estimated_duration_seconds=1.0,
            complexity_level=1,
            response_hint="简短友好，1-2句话，不要提供训练建议"
        )
        
        # 模板1: 完整训练计划
        self.templates["complete_training_plan"] = DAGTemplate(
            template_id="complete_training_plan",
            name="完整训练计划",
            description="为用户制定包含动作选择、训练量计算、周期化安排的完整训练计划",
            category=TemplateCategory.COMPREHENSIVE,
            applicable_intents=[
                "制定训练计划",
                "增肌计划",
                "力量训练计划",
                "完整训练方案",
                "系统训练计划"
            ],
            required_tools=[
                "get_user_profile",
                "contraindications_checker",
                "injury_risk_assessor",
                "intelligent_exercise_selector",
                "muscle_group_volume_calculator",
                "professional_program_designer",
                "intelligent_weight_calculator"  # ✅ 添加：计算个性化训练重量
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
                "movement_pattern_balancer": ["get_user_profile"],
                "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator"],
                "intelligent_weight_calculator": ["intelligent_exercise_selector"],
                "professional_program_designer": ["intelligent_exercise_selector", "muscle_group_volume_calculator", "intelligent_weight_calculator"],
                "periodized_program_designer": ["professional_program_designer"],
                "training_split_designer": ["professional_program_designer"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator", "movement_pattern_balancer"],
                ["intelligent_exercise_selector"],
                ["intelligent_weight_calculator"],
                ["professional_program_designer"],
                ["periodized_program_designer", "training_split_designer"]
            ],
            expected_output={
                "user_profile": "用户档案数据",
                "contraindications": "禁忌动作列表",
                "injury_risks": "损伤风险评估",
                "recommended_exercises": "推荐动作列表",
                "volume_recommendations": "训练量建议",
                "training_program": "完整训练计划"
            },
            safety_constraints=[
                "必须执行contraindications-checker",
                "必须执行injury-risk-assessor",
                "禁忌动作必须从推荐中排除"
            ],
            estimated_duration_seconds=15.0,
            complexity_level=3,
            response_hint="详细专业，提供完整的训练计划，包含动作选择、组数次数、训练量分配、周期化安排，字数300-500字"
        )
        
        # 模板2: 营养规划
        self.templates["nutrition_planning"] = DAGTemplate(
            template_id="nutrition_planning",
            name="营养规划",
            description="基于用户目标和训练计划制定完整的营养方案",
            category=TemplateCategory.NUTRITION,
            applicable_intents=[
                "营养计划",
                "饮食建议",
                "营养规划",
                "膳食计划",
                "营养方案"
            ],
            required_tools=[
                "get_user_profile",
                "tdee_calculator",
                "nutrition_intake_analyzer",
                "meal_plan_designer"
            ],
            optional_tools=[
                "exercise_nutrition_optimization"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "tdee_calculator": ["get_user_profile"],
                "nutrition_intake_analyzer": ["tdee_calculator"],
                "meal_plan_designer": ["tdee_calculator", "nutrition_intake_analyzer"],
                "exercise_nutrition_optimization": ["meal_plan_designer"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["tdee_calculator"],
                ["nutrition_intake_analyzer"],
                ["meal_plan_designer"],
                ["exercise_nutrition_optimization"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "tdee": "每日总能量消耗",
                "nutrition_analysis": "营养摄入分析",
                "meal_plan": "膳食计划"
            },
            safety_constraints=[
                "必须考虑用户饮食偏好",
                "必须考虑食物过敏",
                "必须符合健康饮食原则"
            ],
            estimated_duration_seconds=10.0,
            complexity_level=2,
            response_hint="专业详细，提供完整的营养方案，包含TDEE计算、宏量营养素分配、膳食计划建议，字数200-400字"
        )
        
        # 模板3: 安全评估
        self.templates["safety_assessment"] = DAGTemplate(
            template_id="safety_assessment",
            name="安全评估",
            description="全面评估用户的运动安全性，识别风险和禁忌",
            category=TemplateCategory.SAFETY,
            applicable_intents=[
                "安全评估",
                "风险评估",
                "禁忌检查",
                "安全检查",
                "能否训练"
            ],
            required_tools=[
                "get_user_profile",
                "contraindications_checker",
                "injury_risk_assessor"
            ],
            optional_tools=[
                "safe_exercise_modifier",
                "exercise_alternative_finder"
            ],
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
                "user_profile": "用户档案",
                "contraindications": "禁忌动作",
                "injury_risks": "损伤风险",
                "safety_report": "安全评估报告",
                "safe_alternatives": "安全替代方案"
            },
            safety_constraints=[
                "必须全面检查健康状况",
                "必须识别所有禁忌症",
                "必须提供安全建议"
            ],
            estimated_duration_seconds=8.0,
            complexity_level=2,
            response_hint="专业严谨，重点说明安全风险和禁忌事项，提供具体的安全建议和替代方案，字数150-300字"
        )
        
        # 模板4: 动作优化
        self.templates["exercise_optimization"] = DAGTemplate(
            template_id="exercise_optimization",
            name="动作优化",
            description="优化训练动作选择，提供替代方案和安全调整",
            category=TemplateCategory.TRAINING,
            applicable_intents=[
                "动作推荐",
                "动作选择",
                "动作替代",
                "动作优化",
                "换动作"
            ],
            required_tools=[
                "get_user_profile",
                "intelligent_exercise_selector",
                "exercise_alternative_finder"
            ],
            optional_tools=[
                "contraindications_checker",
                "safe_exercise_modifier",
                "movement_pattern_balancer",
                "intelligent_weight_calculator"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "contraindications_checker": ["get_user_profile"],
                "intelligent_exercise_selector": ["get_user_profile", "contraindications_checker"],
                "exercise_alternative_finder": ["intelligent_exercise_selector"],
                "safe_exercise_modifier": ["intelligent_exercise_selector"],
                "movement_pattern_balancer": ["intelligent_exercise_selector"],
                "intelligent_weight_calculator": ["intelligent_exercise_selector"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["contraindications_checker"],
                ["intelligent_exercise_selector"],
                ["exercise_alternative_finder", "safe_exercise_modifier", "movement_pattern_balancer"],
                ["intelligent_weight_calculator"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "recommended_exercises": "推荐动作",
                "alternatives": "替代动作",
                "modifications": "安全调整",
                "weight_recommendations": "重量建议"
            },
            safety_constraints=[
                "必须考虑用户能力",
                "必须提供安全替代",
                "必须考虑器械可用性"
            ],
            estimated_duration_seconds=6.0,
            complexity_level=1,
            response_hint="简洁实用，重点推荐2-3个动作，说明选择理由和执行要点，提供替代方案，字数100-200字"
        )
        
        # 模板5: 综合健身方案
        self.templates["comprehensive_fitness"] = DAGTemplate(
            template_id="comprehensive_fitness",
            name="综合健身方案",
            description="包含训练、营养、安全的完整健身解决方案",
            category=TemplateCategory.COMPREHENSIVE,
            applicable_intents=[
                "完整方案",
                "综合计划",
                "全面指导",
                "健身方案",
                "系统方案"
            ],
            required_tools=[
                "get_user_profile",
                "contraindications_checker",
                "injury_risk_assessor",
                "intelligent_exercise_selector",
                "muscle_group_volume_calculator",
                "professional_program_designer",
                "tdee_calculator",
                "meal_plan_designer"
            ],
            optional_tools=[
                "periodized_program_designer",
                "training_split_designer",
                "exercise_nutrition_optimization"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "contraindications_checker": ["get_user_profile"],
                "injury_risk_assessor": ["get_user_profile"],
                "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"],
                "muscle_group_volume_calculator": ["get_user_profile"],
                "professional_program_designer": ["intelligent_exercise_selector", "muscle_group_volume_calculator"],
                "tdee_calculator": ["get_user_profile"],
                "meal_plan_designer": ["tdee_calculator", "professional_program_designer"],
                "periodized_program_designer": ["professional_program_designer"],
                "training_split_designer": ["professional_program_designer"],
                "exercise_nutrition_optimization": ["professional_program_designer", "meal_plan_designer"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["contraindications_checker", "injury_risk_assessor", "muscle_group_volume_calculator", "tdee_calculator"],
                ["intelligent_exercise_selector"],
                ["professional_program_designer"],
                ["meal_plan_designer", "periodized_program_designer", "training_split_designer"],
                ["exercise_nutrition_optimization"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "safety_assessment": "安全评估",
                "training_program": "训练计划",
                "nutrition_plan": "营养计划",
                "periodization": "周期化方案",
                "analytics": "数据分析"
            },
            safety_constraints=[
                "必须全面安全评估",
                "训练和营养必须协调",
                "必须考虑恢复能力"
            ],
            estimated_duration_seconds=20.0,
            complexity_level=3,
            response_hint="全面系统，提供训练和营养的完整方案，包含安全评估、训练计划、营养计划、周期化安排，字数500-800字"
        )
        
        # 模板6: 快速咨询
        self.templates["quick_consultation"] = DAGTemplate(
            template_id="quick_consultation",
            name="快速咨询",
            description="快速回答简单的健身问题",
            category=TemplateCategory.QUICK,
            applicable_intents=[
                "简单问题",
                "快速咨询",
                "基础问题",
                "一般咨询"
            ],
            required_tools=[
                "get_user_profile"
            ],
            optional_tools=[
                # 快速咨询不需要复杂的工具，只获取用户档案即可
            ],
            tool_dependencies={
                "get_user_profile": []
            },
            parallel_groups=[
                ["get_user_profile"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "recommendations": "建议",
                "quick_answer": "快速回答"
            },
            safety_constraints=[
                "必须提供准确信息",
                "必须基于科学证据"
            ],
            estimated_duration_seconds=2.0,
            complexity_level=1,
            response_hint="简洁明了，直接回答用户问题，提供实用建议，2-3段话，字数100-200字"
        )
        
        # 模板7: 进展分析
        self.templates["progress_analysis"] = DAGTemplate(
            template_id="progress_analysis",
            name="进展分析",
            description="分析用户训练进展，提供优化建议",
            category=TemplateCategory.TRAINING,
            applicable_intents=[
                "进展分析",
                "数据分析",
                "训练分析",
                "效果评估",
                "进度查看"
            ],
            required_tools=[
                "get_user_profile",
                "muscle_group_volume_calculator"
            ],
            optional_tools=[
                "periodized_program_designer"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "muscle_group_volume_calculator": ["get_user_profile"],
                "periodized_program_designer": ["muscle_group_volume_calculator"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["muscle_group_volume_calculator"],
                ["periodized_program_designer"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "analytics": "训练分析",
                "recommendations": "优化建议",
                "next_steps": "下一步计划"
            },
            safety_constraints=[
                "必须基于真实数据",
                "必须提供可行建议"
            ],
            estimated_duration_seconds=8.0,
            complexity_level=2,
            response_hint="数据驱动，分析训练进展和效果，指出优化方向，提供具体的改进建议，字数200-300字"
        )
        
        # 模板8: 康复训练
        self.templates["rehabilitation_training"] = DAGTemplate(
            template_id="rehabilitation_training",
            name="康复训练",
            description="为有伤病史的用户制定安全的康复训练计划",
            category=TemplateCategory.SAFETY,
            applicable_intents=[
                "康复训练",
                "伤后训练",
                "康复计划",
                "恢复训练",
                "受伤恢复"
            ],
            required_tools=[
                "get_user_profile",
                "contraindications_checker",
                "injury_risk_assessor",
                "safe_exercise_modifier"
            ],
            optional_tools=[
                "exercise_alternative_finder",
                "intelligent_exercise_selector",
                "movement_pattern_balancer"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "contraindications_checker": ["get_user_profile"],
                "injury_risk_assessor": ["get_user_profile"],
                "safe_exercise_modifier": ["injury_risk_assessor"],
                "exercise_alternative_finder": ["contraindications_checker"],
                "intelligent_exercise_selector": ["safe_exercise_modifier"],
                "movement_pattern_balancer": ["intelligent_exercise_selector"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["contraindications_checker", "injury_risk_assessor"],
                ["safe_exercise_modifier"],
                ["exercise_alternative_finder", "intelligent_exercise_selector"],
                ["movement_pattern_balancer"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "safety_assessment": "安全评估",
                "safe_exercises": "安全动作",
                "rehabilitation_plan": "康复计划",
                "progress_monitoring": "进展监控"
            },
            safety_constraints=[
                "必须严格安全评估",
                "必须避免加重伤病",
                "必须循序渐进",
                "必须持续监控"
            ],
            estimated_duration_seconds=12.0,
            complexity_level=3,
            response_hint="谨慎专业，重点强调安全性和循序渐进，提供详细的康复训练计划和注意事项，字数300-400字"
        )
        
        # 模板9: 体态矫正
        self.templates["posture_correction"] = DAGTemplate(
            template_id="posture_correction",
            name="体态矫正",
            description="评估用户体态问题，推荐矫正动作并制定矫正训练计划",
            category=TemplateCategory.SAFETY,
            applicable_intents=[
                "体态矫正",
                "姿势改善",
                "圆肩驼背",
                "骨盆前倾",
                "体态评估",
                "矫正训练",
                "改善体态"
            ],
            required_tools=[
                "get_user_profile",
                "contraindications_checker",
                "intelligent_exercise_selector"
            ],
            optional_tools=[
                "postural_assessor",
                "movement_pattern_balancer",
                "professional_program_designer"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "postural_assessor": ["get_user_profile"],
                "contraindications_checker": ["get_user_profile"],
                "intelligent_exercise_selector": ["contraindications_checker"],
                "movement_pattern_balancer": ["intelligent_exercise_selector"],
                "professional_program_designer": ["movement_pattern_balancer"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["postural_assessor", "contraindications_checker"],
                ["intelligent_exercise_selector"],
                ["movement_pattern_balancer", "professional_program_designer"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "postural_assessment": "体态评估",
                "corrective_exercises": "矫正动作",
                "aggravating_exercises": "加重动作警告",
                "correction_plan": "矫正训练计划"
            },
            safety_constraints=[
                "必须识别体态问题",
                "必须推荐矫正动作",
                "必须警告加重动作",
                "必须循序渐进矫正"
            ],
            estimated_duration_seconds=10.0,
            complexity_level=2,
            response_hint="专业友好，重点说明体态问题的成因和影响，提供系统的矫正训练计划和日常注意事项，字数300-400字"
        )
        
        # 模板10: 训练计划调整
        self.templates["plan_adjustment"] = DAGTemplate(
            template_id="plan_adjustment",
            name="训练计划调整",
            description="根据用户反馈和进展调整现有训练计划，优化动作选择和训练量",
            category=TemplateCategory.TRAINING,
            applicable_intents=[
                "调整计划",
                "修改训练",
                "优化计划",
                "计划调整",
                "训练调整",
                "换动作",
                "调整训练量"
            ],
            required_tools=[
                "get_user_profile",
                "exercise_alternative_finder",
                "muscle_group_volume_calculator"
            ],
            optional_tools=[
                "contraindications_checker",
                "intelligent_exercise_selector",
                "movement_pattern_balancer",
                "professional_program_designer"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "contraindications_checker": ["get_user_profile"],
                "muscle_group_volume_calculator": ["get_user_profile"],
                "intelligent_exercise_selector": ["get_user_profile", "contraindications_checker"],
                "exercise_alternative_finder": ["intelligent_exercise_selector"],
                "movement_pattern_balancer": ["intelligent_exercise_selector"],
                "professional_program_designer": ["movement_pattern_balancer", "muscle_group_volume_calculator", "exercise_alternative_finder"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["contraindications_checker", "muscle_group_volume_calculator"],
                ["intelligent_exercise_selector"],
                ["exercise_alternative_finder", "movement_pattern_balancer"],
                ["professional_program_designer"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "alternative_exercises": "替代动作",
                "volume_adjustments": "训练量调整",
                "adjusted_plan": "调整后的训练计划"
            },
            safety_constraints=[
                "必须考虑用户反馈",
                "必须保持训练连贯性",
                "必须避免过度训练"
            ],
            estimated_duration_seconds=8.0,
            complexity_level=2,
            response_hint="实用灵活，重点说明调整的原因和预期效果，提供具体的替代方案和训练量建议，字数200-300字"
        )
        
        # 模板11: 减脂专项
        self.templates["fat_loss_program"] = DAGTemplate(
            template_id="fat_loss_program",
            name="减脂专项",
            description="制定以减脂为目标的综合训练和营养方案",
            category=TemplateCategory.COMPREHENSIVE,
            applicable_intents=[
                "减脂",
                "减肥",
                "降体脂",
                "减脂计划",
                "减肥方案",
                "瘦身",
                "燃脂训练"
            ],
            required_tools=[
                "get_user_profile",
                "tdee_calculator",
                "intelligent_exercise_selector",
                "muscle_group_volume_calculator",
                "professional_program_designer",
                "meal_plan_designer"
            ],
            optional_tools=[
                "contraindications_checker",
                "nutrition_intake_analyzer",
                "exercise_nutrition_optimization"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "contraindications_checker": ["get_user_profile"],
                "tdee_calculator": ["get_user_profile"],
                "muscle_group_volume_calculator": ["get_user_profile"],
                "intelligent_exercise_selector": ["contraindications_checker", "muscle_group_volume_calculator"],
                "professional_program_designer": ["intelligent_exercise_selector"],
                "nutrition_intake_analyzer": ["tdee_calculator"],
                "meal_plan_designer": ["tdee_calculator", "nutrition_intake_analyzer"],
                "exercise_nutrition_optimization": ["professional_program_designer", "meal_plan_designer"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["contraindications_checker", "tdee_calculator", "muscle_group_volume_calculator"],
                ["intelligent_exercise_selector", "nutrition_intake_analyzer"],
                ["professional_program_designer", "meal_plan_designer"],
                ["exercise_nutrition_optimization"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "tdee": "每日总能量消耗",
                "calorie_deficit": "热量缺口",
                "training_program": "减脂训练计划",
                "nutrition_plan": "减脂营养计划",
                "fat_loss_strategy": "减脂策略"
            },
            safety_constraints=[
                "必须设置合理的热量缺口",
                "必须保持肌肉量",
                "必须避免过度节食",
                "必须考虑营养均衡"
            ],
            estimated_duration_seconds=15.0,
            complexity_level=3,
            response_hint="系统全面，重点说明减脂的科学原理和策略，提供训练和营养的完整方案，强调可持续性，字数400-600字"
        )
        
        # 模板12: 力量专项
        self.templates["strength_program"] = DAGTemplate(
            template_id="strength_program",
            name="力量专项",
            description="制定以增强力量为目标的专项训练计划",
            category=TemplateCategory.TRAINING,
            applicable_intents=[
                "增强力量",
                "力量训练",
                "提高力量",
                "力量计划",
                "大重量训练",
                "最大力量",
                "爆发力训练"
            ],
            required_tools=[
                "get_user_profile",
                "intelligent_exercise_selector",
                "intelligent_weight_calculator",
                "professional_program_designer"
            ],
            optional_tools=[
                "contraindications_checker",
                "injury_risk_assessor",
                "periodized_program_designer",
                "movement_pattern_balancer"
            ],
            tool_dependencies={
                "get_user_profile": [],
                "contraindications_checker": ["get_user_profile"],
                "injury_risk_assessor": ["get_user_profile"],
                "intelligent_exercise_selector": ["contraindications_checker", "injury_risk_assessor"],
                "intelligent_weight_calculator": ["intelligent_exercise_selector"],
                "movement_pattern_balancer": ["intelligent_exercise_selector"],
                "professional_program_designer": ["intelligent_weight_calculator", "movement_pattern_balancer"],
                "periodized_program_designer": ["professional_program_designer"]
            },
            parallel_groups=[
                ["get_user_profile"],
                ["contraindications_checker", "injury_risk_assessor"],
                ["intelligent_exercise_selector"],
                ["intelligent_weight_calculator", "movement_pattern_balancer"],
                ["professional_program_designer"],
                ["periodized_program_designer"]
            ],
            expected_output={
                "user_profile": "用户档案",
                "strength_exercises": "力量训练动作",
                "weight_recommendations": "重量建议",
                "strength_program": "力量训练计划",
                "periodization": "周期化方案"
            },
            safety_constraints=[
                "必须评估力量基础",
                "必须循序渐进增加负重",
                "必须注意动作技术",
                "必须充分恢复"
            ],
            estimated_duration_seconds=12.0,
            complexity_level=3,
            response_hint="专业严谨，重点说明力量训练的原理和方法，提供详细的训练计划和负重建议，强调技术和安全，字数300-500字"
        )
        
        logger.info(f"✅ 初始化了 {len(self.templates)} 个DAG模板")
    
    def _validate_all_templates(self):
        """验证所有模板"""
        invalid_templates = []
        for template_id, template in self.templates.items():
            if not template.validate():
                invalid_templates.append(template_id)
        
        if invalid_templates:
            logger.error(f"❌ 以下模板验证失败: {invalid_templates}")
            raise ValueError(f"模板验证失败: {invalid_templates}")
        
        logger.info(f"✅ 所有 {len(self.templates)} 个模板验证通过")
    
    def get_template(self, template_id: str) -> Optional[DAGTemplate]:
        """获取指定模板"""
        return self.templates.get(template_id)
    
    def get_all_templates(self) -> List[DAGTemplate]:
        """获取所有模板"""
        return list(self.templates.values())
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[DAGTemplate]:
        """按类别获取模板"""
        return [t for t in self.templates.values() if t.category == category]
    
    def get_templates_for_llm(self) -> str:
        """获取格式化的模板列表供LLM选择"""
        template_descriptions = []
        
        for template in self.templates.values():
            desc = f"""
### {template.name} (ID: {template.template_id})
- **描述**: {template.description}
- **类别**: {template.category.value}
- **适用场景**: {', '.join(template.applicable_intents)}
- **复杂度**: {'⭐' * template.complexity_level}
- **预计耗时**: {template.estimated_duration_seconds}秒
- **必需工具**: {len(template.required_tools)}个
- **可选工具**: {len(template.optional_tools)}个
"""
            template_descriptions.append(desc)
        
        return "\n".join(template_descriptions)
    
    def search_templates(self, query: str) -> List[DAGTemplate]:
        """搜索模板"""
        query_lower = query.lower()
        matching_templates = []
        
        for template in self.templates.values():
            # 检查名称
            if query_lower in template.name.lower():
                matching_templates.append(template)
                continue
            
            # 检查描述
            if query_lower in template.description.lower():
                matching_templates.append(template)
                continue
            
            # 检查适用意图
            for intent in template.applicable_intents:
                if query_lower in intent.lower():
                    matching_templates.append(template)
                    break
        
        return matching_templates
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """获取模板统计信息"""
        stats = {
            "total_templates": len(self.templates),
            "by_category": {},
            "by_complexity": {1: 0, 2: 0, 3: 0},
            "average_duration": 0.0,
            "total_tools": set()
        }
        
        total_duration = 0.0
        for template in self.templates.values():
            # 按类别统计
            category = template.category.value
            if category not in stats["by_category"]:
                stats["by_category"][category] = 0
            stats["by_category"][category] += 1
            
            # 按复杂度统计
            stats["by_complexity"][template.complexity_level] += 1
            
            # 累计时长
            total_duration += template.estimated_duration_seconds
            
            # 收集所有工具
            stats["total_tools"].update(template.required_tools)
            stats["total_tools"].update(template.optional_tools)
        
        stats["average_duration"] = total_duration / len(self.templates)
        stats["total_tools"] = len(stats["total_tools"])
        
        return stats
    
    def export_templates(self, filepath: str):
        """导出模板到JSON文件"""
        templates_data = {
            template_id: template.to_dict()
            for template_id, template in self.templates.items()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ 导出 {len(self.templates)} 个模板到 {filepath}")
    
    def validate_template_dependencies(self, template_id: str) -> Dict[str, Any]:
        """验证模板的依赖关系"""
        template = self.get_template(template_id)
        if not template:
            return {"valid": False, "error": "模板不存在"}
        
        all_tools = set(template.required_tools + template.optional_tools)
        issues = []
        
        # 检查循环依赖
        def has_cycle(tool: str, visited: Set[str], rec_stack: Set[str]) -> bool:
            visited.add(tool)
            rec_stack.add(tool)
            
            for dep in template.tool_dependencies.get(tool, []):
                if dep not in visited:
                    if has_cycle(dep, visited, rec_stack):
                        return True
                elif dep in rec_stack:
                    return True
            
            rec_stack.remove(tool)
            return False
        
        for tool in all_tools:
            if has_cycle(tool, set(), set()):
                issues.append(f"检测到循环依赖: {tool}")
        
        # 检查依赖完整性
        for tool, deps in template.tool_dependencies.items():
            for dep in deps:
                if dep not in all_tools:
                    issues.append(f"工具 {tool} 的依赖 {dep} 不在工具列表中")
        
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "total_tools": len(all_tools),
            "total_dependencies": sum(len(deps) for deps in template.tool_dependencies.values())
        }


# 使用示例
if __name__ == "__main__":
    # 初始化模板管理器
    manager = DAGTemplateManager()
    
    # 获取所有模板
    print(f"总共 {len(manager.get_all_templates())} 个模板")
    
    # 获取特定模板
    template = manager.get_template("complete_training_plan")
    if template:
        print(f"\n模板: {template.name}")
        print(f"描述: {template.description}")
        print(f"必需工具: {len(template.required_tools)}")
        print(f"可选工具: {len(template.optional_tools)}")
    
    # 获取LLM格式的模板列表
    llm_templates = manager.get_templates_for_llm()
    print(f"\nLLM模板列表:\n{llm_templates[:500]}...")
    
    # 获取统计信息
    stats = manager.get_template_statistics()
    print(f"\n模板统计:")
    print(f"总模板数: {stats['total_templates']}")
    print(f"按类别: {stats['by_category']}")
    print(f"按复杂度: {stats['by_complexity']}")
    print(f"平均耗时: {stats['average_duration']:.1f}秒")
    print(f"涉及工具: {stats['total_tools']}个")
    
    # 验证依赖关系
    validation = manager.validate_template_dependencies("complete_training_plan")
    print(f"\n依赖验证: {'✅ 通过' if validation['valid'] else '❌ 失败'}")
    if not validation['valid']:
        print(f"问题: {validation['issues']}")
