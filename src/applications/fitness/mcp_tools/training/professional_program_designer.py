"""
专业程序设计器 MCP工具

综合多个工具结果生成完整训练计划
整合动作选择、训练量计算、安全检查等功能

功能特性：
- 调用intelligent_exercise_selector获取动作推荐
- 调用muscle_group_volume_calculator获取训练量
- 调用contraindications_checker确保安全
- 整合结果生成完整训练计划
- 确保肌群训练平衡和充分恢复
- 自动生成专业热身和放松动作（v2.0.0新增）

作者: BUILD_BODY Team
版本: v2.0.0
日期: 2026-01-06
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
import logging

from ..base_tool import BaseMCPTool
from ...services.warmup_cooldown_exercises import (
    WarmupCooldownSelector,
    TrainingFocus,
)

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举类型定义
# =============================================================================

class TrainingGoal(str, Enum):
    """
    训练目标枚举
    
    包含基础训练目标和中国本地化扩展目标
    Requirements: 3.1, 3.2, 3.3
    """
    # 基础训练目标
    STRENGTH = "strength"                    # 力量提升
    HYPERTROPHY = "hypertrophy"              # 增肌
    ENDURANCE = "endurance"                  # 耐力
    GENERAL_FITNESS = "general_fitness"      # 综合健身
    
    # 中国本地化扩展目标 - Requirements 3.1, 3.2, 3.3
    FAT_LOSS = "fat_loss"                    # 减脂塑形 - Requirements 3.1
    POSTURE_CORRECTION = "posture_correction"  # 体态矫正 - Requirements 3.2
    FUNCTIONAL = "functional"                # 功能性训练 - Requirements 3.3


class TrainingSplit(str, Enum):
    """训练分化"""
    FULL_BODY = "full_body"
    UPPER_LOWER = "upper_lower"
    PUSH_PULL_LEGS = "push_pull_legs"
    BRO_SPLIT = "bro_split"


class DifficultyLevel(str, Enum):
    """难度等级"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


# =============================================================================
# 输入Schema定义
# =============================================================================

class ProfessionalProgramDesignerInput(BaseModel):
    """专业程序设计器输入Schema"""
    
    # 用户信息
    user_id: str = Field(..., description="用户ID")
    
    # 训练目标
    training_goal: TrainingGoal = Field(..., description="训练目标")
    training_split: TrainingSplit = Field(..., description="训练分化方式")
    training_days_per_week: int = Field(..., ge=1, le=7, description="每周训练天数")
    
    # 用户水平
    difficulty_level: DifficultyLevel = Field(..., description="难度等级")
    
    # 器械和限制
    available_equipment: List[str] = Field(..., description="可用器械列表")
    injury_history: Optional[List[str]] = Field(None, description="损伤历史（可选）")
    
    # 目标肌群（可选，如果不指定则根据训练分化自动选择）
    target_muscle_groups: Optional[List[str]] = Field(None, description="目标肌群列表（可选）")
    
    # 偏好设置
    session_duration_minutes: Optional[int] = Field(60, ge=30, le=180, description="单次训练时长（分钟）")
    include_warmup: bool = Field(True, description="是否包含热身")
    include_cooldown: bool = Field(True, description="是否包含放松")
    
    # 训练周期参数（新增）
    training_weeks: Optional[int] = Field(4, ge=1, le=16, description="训练周数（默认4周）")
    rest_pattern: Optional[str] = Field(None, description="休息模式（如'练三休一'、'练六休一'）")


# =============================================================================
# 输出Schema定义
# =============================================================================

class ExerciseInProgram(BaseModel):
    """
    计划中的动作（精简版）
    
    设计原则：
    - 只保留核心训练参数，节省LLM token
    - 动作详情（肌群、安全注意事项、执行要点）通过exercise_id跳转详情页查看
    - 详情页数据来自Neo4j数据库（1790个动作），不消耗LLM token
    
    Token优化效果：
    - 原结构每个动作约100-150 tokens
    - 精简后每个动作约20-30 tokens
    - 18个动作可节省约1500-2000 tokens
    
    版本: v2.0.0
    更新日期: 2025-01-02
    """
    exercise_id: str = Field(..., description="动作ID，用于跳转详情页")
    name_zh: str = Field(..., description="动作中文名称")
    
    # 核心训练参数
    sets: int = Field(..., description="组数")
    reps_range: tuple[int, int] = Field(..., description="次数范围，如(8,12)")
    rest_seconds: int = Field(..., description="组间休息时间（秒）")
    
    # 可选：个性化重量建议
    weight: Optional[str] = Field(None, description="个性化重量建议，如'60kg起步'或'自重'")


class TrainingDay(BaseModel):
    """训练日"""
    day_number: int
    day_name: str
    focus_muscle_groups: List[str]
    exercises: List[ExerciseInProgram]
    total_sets: int
    estimated_duration_minutes: int


class WeeklyProgram(BaseModel):
    """周训练计划"""
    week_number: int
    training_days: List[TrainingDay]
    rest_days: List[int]
    total_weekly_sets: int
    muscle_group_distribution: Dict[str, int]
    # 新增周期信息
    cycle_days: Optional[int] = None
    cycles_per_week: Optional[float] = None
    training_pattern: Optional[str] = None


class ProgramBalance(BaseModel):
    """计划平衡性分析"""
    muscle_group_coverage: Dict[str, str]  # 肌群 -> 覆盖状态（充分/适中/不足）
    movement_pattern_balance: Dict[str, int]  # 动作模式 -> 次数
    push_pull_ratio: str
    compound_isolation_ratio: str
    balance_score: float
    recommendations: List[str]


class SafetyAssessment(BaseModel):
    """
    安全评估（优化版）
    
    设计原则：
    - safety_recommendations: 只保留个性化的安全建议（如"因您有腰椎问题，避免大重量硬拉"）
    - personalized_notes: 个性化调整说明（如"因肩伤选择了低位卧推替代上斜卧推"）
    - 通用安全提示（如"训练前热身"）不需要LLM生成，前端固定显示
    
    版本: v2.0.0
    更新日期: 2025-01-02
    """
    overall_risk_level: Literal["LOW", "MODERATE", "HIGH", "CRITICAL"]
    contraindications_found: int = Field(default=0, description="发现的禁忌症数量")
    safety_recommendations: List[str] = Field(default_factory=list, description="个性化安全建议")
    personalized_notes: List[str] = Field(default_factory=list, description="个性化调整说明，解释为什么选择/替换某些动作")
    medical_consultation_needed: bool = Field(default=False, description="是否需要医学咨询")


class ProfessionalProgramDesignerOutput(BaseModel):
    """专业程序设计器输出Schema"""
    
    success: bool
    tool_name: str
    user_id: str
    
    # 计划概览
    program_overview: Dict[str, Any]
    
    # 周训练计划
    weekly_program: WeeklyProgram
    
    # 平衡性分析
    program_balance: ProgramBalance
    
    # 安全评估
    safety_assessment: SafetyAssessment
    
    # 执行建议
    execution_guidelines: List[str]
    
    # 注意事项
    important_notes: List[str]
    
    # 元数据
    execution_time_ms: float
    confidence_score: float
    tools_called: List[str]


# =============================================================================
# 专业程序设计器类
# =============================================================================

class ProfessionalProgramDesigner(BaseMCPTool):
    """
    专业程序设计器
    
    整合多个MCP工具生成完整训练计划：
    - intelligent_exercise_selector: 获取动作推荐
    - muscle_group_volume_calculator: 获取训练量
    - contraindications_checker: 确保安全
    """
    
    def __init__(
        self,
        neo4j_client,
        qdrant_client,
        three_layer_engine,
        logger: Optional[logging.Logger] = None,
        tool_registry=None
    ):
        """
        初始化专业程序设计器
        
        Args:
            neo4j_client: Neo4j客户端实例
            qdrant_client: Qdrant客户端实例
            three_layer_engine: 三层检索引擎实例
            logger: 日志记录器（可选）
            tool_registry: 工具注册表（用于调用其他工具）
        """
        super().__init__(neo4j_client, qdrant_client, three_layer_engine, logger)
        self.tool_registry = tool_registry
    
    def get_name(self) -> str:
        return "professional_program_designer"
    
    def get_description(self) -> str:
        return "专业程序设计器 - 整合多个工具生成完整训练计划，确保肌群平衡和充分恢复"
    
    def get_category(self) -> str:
        return "training"
    
    def get_input_schema(self) -> type[BaseModel]:
        return ProfessionalProgramDesignerInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return ProfessionalProgramDesignerOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 5000.0  # 5秒（需要调用多个工具）
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return [
            "neo4j",
            "qdrant",
            "three_layer_engine",
            "intelligent_exercise_selector",
            "muscle_group_volume_calculator",
            "contraindications_checker"
        ]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行专业程序设计
        
        流程：
        1. 确定目标肌群（基于训练分化）
        2. 为每周生成训练计划（应用周期化训练量）
        3. 整合结果生成多周训练计划
        4. 分析计划平衡性
        5. 进行安全评估
        6. 生成执行建议
        """
        import time
        start_time = time.time()
        
        tools_called = []
        
        try:
            # Step 1: 确定适用的训练标准
            applicable_standard = self._determine_applicable_standard(input_data)
            
            self.logger.info(
                f"📚 确定训练标准: {applicable_standard['standard_name']}, "
                f"原因: {applicable_standard['application_reason'][:50]}..."
            )
            
            # Step 2: 计算训练周期
            cycle_info = self._calculate_training_cycle(input_data)
            
            # Step 3: 确定目标肌群
            target_muscle_groups = self._determine_target_muscle_groups(input_data)
            
            # Step 4: 获取训练周数
            training_weeks = input_data.get("training_weeks", 4)
            
            # Step 5: 为每周生成训练计划（应用周期化训练量）
            weekly_programs = []
            
            for week_num in range(1, training_weeks + 1):
                # 为每个肌群获取推荐（传递周数以应用周期化训练量）
                muscle_group_data = await self._gather_muscle_group_data(
                    input_data,
                    target_muscle_groups,
                    tools_called,
                    week_number=week_num
                )
                
                # 生成该周的训练计划
                weekly_program = self._generate_weekly_program(
                    input_data,
                    muscle_group_data,
                    cycle_info
                )
                
                # 设置周数
                weekly_program["week_number"] = week_num
                
                # 添加周期化信息
                if week_num in [1, 2]:
                    weekly_program["periodization_phase"] = "积累期"
                    weekly_program["phase_description"] = "使用最大适应训练量（MAV），诱导肌肥大适应"
                elif week_num == 3:
                    weekly_program["periodization_phase"] = "冲刺期"
                    weekly_program["phase_description"] = "使用最大可恢复训练量（MRV），达到训练峰值"
                elif week_num == 4:
                    weekly_program["periodization_phase"] = "减量期"
                    weekly_program["phase_description"] = "使用最小有效训练量（MEV），促进超量恢复"
                else:
                    # 超过4周的情况，循环使用周期
                    cycle_week = ((week_num - 1) % 4) + 1
                    if cycle_week in [1, 2]:
                        weekly_program["periodization_phase"] = "积累期"
                        weekly_program["phase_description"] = "使用最大适应训练量（MAV），诱导肌肥大适应"
                    elif cycle_week == 3:
                        weekly_program["periodization_phase"] = "冲刺期"
                        weekly_program["phase_description"] = "使用最大可恢复训练量（MRV），达到训练峰值"
                    else:
                        weekly_program["periodization_phase"] = "减量期"
                        weekly_program["phase_description"] = "使用最小有效训练量（MEV），促进超量恢复"
                
                weekly_programs.append(weekly_program)
                
                self.logger.info(
                    f"📅 第{week_num}训练周期计划生成完成: "
                    f"阶段={weekly_program['periodization_phase']}, "
                    f"总组数={weekly_program['total_weekly_sets']}"
                )
            
            # Step 6: 使用第1周的数据进行平衡性分析（作为基准）
            first_week_program = weekly_programs[0]
            first_week_muscle_data = await self._gather_muscle_group_data(
                input_data,
                target_muscle_groups,
                tools_called,
                week_number=1
            )
            
            program_balance = self._analyze_program_balance(
                first_week_program,
                first_week_muscle_data
            )
            
            # Step 7: 进行安全评估（使用第1周的数据）
            safety_assessment = await self._perform_safety_assessment(
                first_week_program,
                input_data,
                tools_called
            )
            
            # Step 8: 生成执行建议（包含周期化信息和标准引用）
            execution_guidelines = self._generate_execution_guidelines(
                input_data,
                first_week_program,
                program_balance,
                safety_assessment,
                applicable_standard
            )
            
            # 添加周期化训练建议
            execution_guidelines.extend([
                f"周期化训练：第1-2训练周期积累期（MAV），第3训练周期冲刺期（MRV），第4训练周期减量期（MEV）",
                "训练量波动：根据训练周期调整训练量，避免过度训练和停滞",
                "监控恢复：注意疲劳累积，必要时提前进入减量训练周期"
            ])
            
            # Step 9: 生成注意事项
            important_notes = self._generate_important_notes(
                input_data,
                safety_assessment,
                program_balance,
                first_week_program
            )
            
            # 添加周期化注意事项
            important_notes.extend([
                "⚠️ 第3训练周期（冲刺期）训练量最大，注意监控疲劳水平",
                "✅ 第4训练周期（减量期）是恢复期，不要跳过或增加训练量",
                "📊 记录每个训练周期的训练感受，根据恢复情况调整下一周期"
            ])
            
            # 生成计划概览
            total_exercises = sum(
                len(day["exercises"])
                for week in weekly_programs
                for day in week["training_days"]
            )
            
            total_weekly_sets_avg = sum(
                week["total_weekly_sets"]
                for week in weekly_programs
            ) / len(weekly_programs)
            
            # 统计所有周的减量日信息
            total_deload_days = sum(
                week.get("deload_days_count", 0)
                for week in weekly_programs
            )
            
            program_overview = {
                "training_goal": input_data["training_goal"],
                "training_split": input_data["training_split"],
                "training_days_per_week": input_data["training_days_per_week"],
                "difficulty_level": input_data["difficulty_level"],
                "total_exercises": total_exercises,
                "average_weekly_sets": int(total_weekly_sets_avg),
                "estimated_weekly_duration_minutes": sum(
                    day["estimated_duration_minutes"] for day in first_week_program["training_days"]
                ),
                # 新增周期信息
                "training_weeks": training_weeks,
                "cycle_days": cycle_info["cycle_days"],
                "cycles_per_week": cycle_info["cycles_per_week"],
                "training_pattern": cycle_info["training_pattern"],
                "total_cycles": int(cycle_info["cycles_per_week"] * training_weeks),
                # 周期化信息
                "periodization_model": "4周周期化模型",
                "week_1_2_phase": "积累期（MAV）",
                "week_3_phase": "冲刺期（MRV）",
                "week_4_phase": "减量期（MEV）",
                # 减量日信息
                "has_deload_days": total_deload_days > 0,
                "total_deload_days": total_deload_days,
                "deload_day_description": "连续训练≥3天时自动插入减量日，训练量50%，强度80%",
                # 科学依据信息
                "scientific_basis": {
                    "standard_name": applicable_standard["standard_name"],
                    "standard_full_name": applicable_standard["standard_full_name"],
                    "standard_description": applicable_standard["standard_description"],
                    "application_reason": applicable_standard["application_reason"],
                    "key_principles": applicable_standard["key_principles"],
                    "reference": applicable_standard["reference"],
                    "适用场景": applicable_standard["适用场景"]
                }
            }
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": self.get_name(),
                "user_id": input_data["user_id"],
                "program_overview": program_overview,
                "weekly_programs": weekly_programs,  # 返回多周计划
                "weekly_program": first_week_program,  # 保留第1周作为兼容性
                "program_balance": program_balance,
                "safety_assessment": safety_assessment,
                "execution_guidelines": execution_guidelines,
                "important_notes": important_notes,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 90.0,
                "tools_called": tools_called
            }
            
            self.logger.info(
                f"✅ 专业程序设计完成: {input_data['training_split']}, "
                f"{len(first_week_program['training_days'])}天/周, "
                f"平均{int(total_weekly_sets_avg)}组/周, "
                f"周期={cycle_info['cycle_days']}天, "
                f"模式={cycle_info['training_pattern']}, "
                f"总周数={training_weeks}周, "
                f"周期化模型=4周（积累-冲刺-减量）, "
                f"减量日={total_deload_days}天"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 专业程序设计失败: {e}", exc_info=True)
            raise
    
    def _calculate_training_cycle(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算实际训练周期
        
        根据训练分化类型和训练频率计算实际的训练周期：
        - 三分化（推拉腿）+ 练三休一 = 4天周期
        - 三分化（推拉腿）+ 练六休一 = 7天周期
        - 上下肢分化 + 练二休一 = 3天周期
        - 全身训练 = 按训练天数计算
        
        Returns:
            Dict包含：
            - cycle_days: 实际周期天数
            - cycles_per_week: 每周完整周期数
            - training_pattern: 训练模式描述
        """
        training_split = input_data["training_split"]
        training_days_per_week = input_data["training_days_per_week"]
        rest_pattern = input_data.get("rest_pattern")
        
        # 根据训练分化确定基础周期
        if training_split == "push_pull_legs":
            # 推拉腿分化：3个训练日为一个周期
            base_cycle = 3
            
            # 根据训练频率计算实际周期
            if training_days_per_week == 3:
                # 练三休一：3训练 + 1休息 = 4天周期
                cycle_days = 4
                training_pattern = "练三休一"
            elif training_days_per_week == 6:
                # 练六休一：连续两个周期 + 1休息 = 7天周期
                cycle_days = 7
                training_pattern = "练六休一"
            else:
                # 其他情况：按7天计算
                cycle_days = 7
                training_pattern = f"每周{training_days_per_week}天"
        
        elif training_split == "upper_lower":
            # 上下肢分化：2个训练日为一个周期
            base_cycle = 2
            
            if training_days_per_week == 4:
                # 练二休一：2训练 + 1休息 = 3天周期，一周两个周期
                cycle_days = 3
                training_pattern = "练二休一"
            else:
                # 其他情况：按7天计算
                cycle_days = 7
                training_pattern = f"每周{training_days_per_week}天"
        
        elif training_split == "full_body":
            # 全身训练：每次训练都是完整周期
            base_cycle = 1
            
            if training_days_per_week == 3:
                # 练一休一：1训练 + 1休息 = 2天周期
                cycle_days = 2
                training_pattern = "练一休一"
            else:
                # 其他情况：按7天计算
                cycle_days = 7
                training_pattern = f"每周{training_days_per_week}天"
        
        elif training_split == "bro_split":
            # 部位分化：5-7个训练日为一个周期
            base_cycle = 5
            cycle_days = 7
            training_pattern = f"每周{training_days_per_week}天"
        
        else:
            # 默认：按7天计算
            base_cycle = training_days_per_week
            cycle_days = 7
            training_pattern = f"每周{training_days_per_week}天"
        
        # 计算每周完整周期数
        cycles_per_week = 7.0 / cycle_days
        
        self.logger.info(
            f"📊 训练周期计算: {training_split}, "
            f"周期={cycle_days}天, "
            f"每周{cycles_per_week:.1f}个周期, "
            f"模式={training_pattern}"
        )
        
        return {
            "cycle_days": cycle_days,
            "cycles_per_week": cycles_per_week,
            "training_pattern": training_pattern,
            "base_cycle": base_cycle
        }
    
    def _determine_applicable_standard(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        确定适用的训练标准（ACSM或NSCA）
        
        根据用户训练水平和训练目标选择合适的标准：
        - ACSM FITT原则：适用于初学者和一般健身人群
        - NSCA周期化模型：适用于中高级训练者和运动员
        
        Returns:
            Dict包含：
            - standard_name: 标准名称（ACSM或NSCA）
            - standard_description: 标准描述
            - application_reason: 选择该标准的原因
            - key_principles: 关键原则
        """
        difficulty_level = input_data.get("difficulty_level", "intermediate")
        training_goal = input_data.get("training_goal", "general_fitness")
        
        # 根据训练水平和目标确定标准
        if difficulty_level == "beginner":
            # 初学者：使用ACSM FITT原则
            return {
                "standard_name": "ACSM FITT原则",
                "standard_full_name": "美国运动医学会（ACSM）FITT-VP原则",
                "standard_description": "ACSM FITT原则是针对一般健康人群的基础训练指南，强调频率、强度、时间、类型的科学配置",
                "application_reason": f"您的训练水平为初学者，ACSM FITT原则提供了安全、渐进的训练框架，适合建立运动基础和培养训练习惯",
                "key_principles": [
                    "Frequency（频率）：力量训练2-3天/周，确保充分恢复",
                    "Intensity（强度）：60-80% 1RM，适合肌肉适应和技术学习",
                    "Time（时间）：每个肌群2-4组，每组8-12次",
                    "Type（类型）：多样化动作选择，包含复合和孤立动作",
                    "Volume（容量）：渐进增加训练量，遵循10%原则",
                    "Progression（进阶）：每2-4周评估并调整训练参数"
                ],
                "reference": "ACSM's Guidelines for Exercise Testing and Prescription (11th Edition)",
                "适用场景": ["健身初学者", "一般健康人群", "康复训练者", "体重管理"]
            }
        
        elif difficulty_level == "intermediate":
            # 中级：根据目标选择
            if training_goal in ["strength", "hypertrophy"]:
                # 力量/肌肥大目标：使用NSCA周期化模型
                return {
                    "standard_name": "NSCA周期化模型",
                    "standard_full_name": "美国国家体能协会（NSCA）周期化训练模型",
                    "standard_description": "NSCA周期化模型通过系统性地变化训练强度和容量，优化训练适应和防止平台期",
                    "application_reason": f"您的训练水平为中级，且目标为{training_goal}，NSCA周期化模型能够通过科学的训练周期安排，突破训练平台期，实现持续进步",
                    "key_principles": [
                        "线性周期化：肥大期(65-75% 1RM, 8-12次) → 力量期(85-95% 1RM, 2-6次)",
                        "波动周期化：每周变化训练强度和容量，防止适应性停滞",
                        "训练量管理：MEV（最小有效量）→ MAV（最大适应量）→ MRV（最大可恢复量）",
                        "减量周期：每4周安排1周减量期，促进超量恢复",
                        "渐进超负荷：系统性增加训练负荷，确保持续适应"
                    ],
                    "reference": "NSCA's Essentials of Strength Training and Conditioning (4th Edition)",
                    "适用场景": ["中高级训练者", "力量提升", "肌肥大训练", "运动表现"]
                }
            else:
                # 其他目标：使用ACSM FITT原则
                return {
                    "standard_name": "ACSM FITT原则",
                    "standard_full_name": "美国运动医学会（ACSM）FITT-VP原则",
                    "standard_description": "ACSM FITT原则是针对一般健康人群的基础训练指南，强调频率、强度、时间、类型的科学配置",
                    "application_reason": f"您的训练目标为{training_goal}，ACSM FITT原则提供了全面、平衡的训练框架，适合健康促进和体能提升",
                    "key_principles": [
                        "Frequency（频率）：力量训练2-3天/周，有氧训练3-5天/周",
                        "Intensity（强度）：力量60-80% 1RM，有氧50-70% HRmax",
                        "Time（时间）：力量训练每个肌群2-4组，有氧30-60分钟",
                        "Type（类型）：多样化运动选择，结合力量和有氧训练",
                        "Volume（容量）：根据个体恢复能力调整训练量",
                        "Progression（进阶）：渐进增加训练负荷，遵循10%原则"
                    ],
                    "reference": "ACSM's Guidelines for Exercise Testing and Prescription (11th Edition)",
                    "适用场景": ["健康促进", "体重管理", "一般体能提升", "耐力训练"]
                }
        
        elif difficulty_level in ["advanced", "elite"]:
            # 高级/精英：使用NSCA周期化模型
            return {
                "standard_name": "NSCA高级周期化模型",
                "standard_full_name": "美国国家体能协会（NSCA）高级周期化训练模型",
                "standard_description": "NSCA高级周期化模型针对有经验的训练者，通过复杂的周期安排和专项训练，实现运动表现的最大化",
                "application_reason": f"您的训练水平为{difficulty_level}，NSCA高级周期化模型提供了精细的训练周期管理和专项能力发展策略，适合追求极致表现",
                "key_principles": [
                    "分块周期化：专注特定能力发展（力量块、爆发力块、耐力块）",
                    "波动周期化：日常、周、月多层次训练变化",
                    "高级训练量管理：精确控制MEV/MAV/MRV，优化训练刺激",
                    "专项训练整合：结合运动专项需求，定制训练方案",
                    "恢复策略：主动恢复、营养时机、睡眠优化",
                    "监控与调整：基于表现数据实时调整训练计划"
                ],
                "reference": "NSCA's Essentials of Strength Training and Conditioning (4th Edition), Periodization Training for Sports (Bompa & Haff)",
                "适用场景": ["高级训练者", "竞技运动员", "力量举/健美", "运动表现优化"]
            }
        
        else:
            # 默认：使用ACSM FITT原则
            return {
                "standard_name": "ACSM FITT原则",
                "standard_full_name": "美国运动医学会（ACSM）FITT-VP原则",
                "standard_description": "ACSM FITT原则是针对一般健康人群的基础训练指南",
                "application_reason": "基于您的情况，ACSM FITT原则提供了安全、有效的训练框架",
                "key_principles": [
                    "Frequency（频率）：力量训练2-3天/周",
                    "Intensity（强度）：60-80% 1RM",
                    "Time（时间）：每个肌群2-4组",
                    "Type（类型）：多样化动作选择"
                ],
                "reference": "ACSM's Guidelines for Exercise Testing and Prescription",
                "适用场景": ["一般健身人群"]
            }
    
    def _determine_target_muscle_groups(
        self,
        input_data: Dict[str, Any]
    ) -> List[str]:
        """
        确定目标肌群（基于训练分化）
        """
        # 如果用户指定了目标肌群，直接使用
        if input_data.get("target_muscle_groups"):
            return input_data["target_muscle_groups"]
        
        # 否则根据训练分化自动选择
        training_split = input_data["training_split"]
        
        if training_split == "full_body":
            return ["胸大肌", "背阔肌", "股四头肌", "腘绳肌", "三角肌", "肱二头肌", "肱三头肌"]
        
        elif training_split == "upper_lower":
            return ["胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌", "股四头肌", "腘绳肌", "臀大肌"]
        
        elif training_split == "push_pull_legs":
            return ["胸大肌", "三角肌", "肱三头肌", "背阔肌", "肱二头肌", "股四头肌", "腘绳肌", "臀大肌"]
        
        elif training_split == "bro_split":
            return ["胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌", "股四头肌", "腘绳肌"]
        
        else:
            # 默认全身训练
            return ["胸大肌", "背阔肌", "股四头肌", "腘绳肌", "三角肌"]
    
    async def _gather_muscle_group_data(
        self,
        input_data: Dict[str, Any],
        target_muscle_groups: List[str],
        tools_called: List[str],
        week_number: int = 1
    ) -> Dict[str, Dict[str, Any]]:
        """
        为每个肌群收集数据（调用工具）
        
        Args:
            input_data: 输入数据
            target_muscle_groups: 目标肌群列表
            tools_called: 已调用工具列表
            week_number: 当前周数（用于周期化训练量调整）
        """
        muscle_group_data = {}
        
        for muscle_group in target_muscle_groups:
            # 调用intelligent_exercise_selector获取动作推荐
            exercise_recommendations = await self._call_exercise_selector(
                input_data,
                muscle_group
            )
            tools_called.append("intelligent_exercise_selector")
            
            # 调用muscle_group_volume_calculator获取训练量（传递周数）
            volume_data = await self._call_volume_calculator(
                input_data,
                muscle_group,
                week_number
            )
            tools_called.append("muscle_group_volume_calculator")
            
            muscle_group_data[muscle_group] = {
                "exercise_recommendations": exercise_recommendations,
                "volume_data": volume_data
            }
        
        return muscle_group_data
    
    async def _call_exercise_selector(
        self,
        input_data: Dict[str, Any],
        muscle_group: str
    ) -> Dict[str, Any]:
        """调用intelligent_exercise_selector工具"""
        if not self.tool_registry:
            self.logger.warning("工具注册表未设置，返回空推荐")
            return {
                "recommendations": [],
                "total_found": 0
            }
        
        try:
            # 构建输入参数
            selector_input = {
                "user_id": input_data["user_id"],
                "muscle_group": muscle_group,
                "training_goal": input_data["training_goal"],
                "difficulty_level": input_data["difficulty_level"],
                "available_equipment": input_data["available_equipment"],
                "injury_history": input_data.get("injury_history"),
                "session_focus": None  # 可以根据训练分化设置
            }
            
            # 调用工具
            result = await self.tool_registry.call_tool(
                "intelligent_exercise_selector",
                selector_input
            )
            
            if result.get("success"):
                return result
            else:
                self.logger.error(f"动作选择失败: {result.get('error')}")
                return {
                    "recommendations": [],
                    "total_found": 0
                }
        
        except Exception as e:
            self.logger.error(f"调用intelligent_exercise_selector失败: {e}", exc_info=True)
            return {
                "recommendations": [],
                "total_found": 0
            }
    
    def adjust_volume_by_level(
        self,
        volume_data: Dict[str, Any],
        fitness_level: str
    ) -> Dict[str, Any]:
        """
        根据训练水平调整训练量
        
        训练水平系数：
        - beginner（初学者）: 0.7
        - intermediate（中级）: 1.0
        - advanced（高级）: 1.2
        - elite（精英）: 1.4
        
        Args:
            volume_data: 原始训练量数据（包含MEV/MAV/MRV）
            fitness_level: 训练水平（beginner/intermediate/advanced/elite）
        
        Returns:
            调整后的训练量数据
        """
        # 定义训练水平系数
        level_coefficients = {
            "beginner": 0.7,
            "intermediate": 1.0,
            "advanced": 1.2,
            "elite": 1.4
        }
        
        # 获取系数，默认为中级（1.0）
        coefficient = level_coefficients.get(fitness_level, 1.0)
        
        # 复制原始数据
        adjusted_data = volume_data.copy()
        
        # 调整MEV/MAV/MRV值
        if "mev" in adjusted_data:
            adjusted_data["mev"] = int(adjusted_data["mev"] * coefficient)
        
        if "mav" in adjusted_data:
            adjusted_data["mav"] = int(adjusted_data["mav"] * coefficient)
        
        if "mrv" in adjusted_data:
            adjusted_data["mrv"] = int(adjusted_data["mrv"] * coefficient)
        
        # 调整volume_recommendation中的训练量
        if "volume_recommendation" in adjusted_data:
            vol_rec = adjusted_data["volume_recommendation"]
            
            if "recommended_weekly_sets" in vol_rec:
                vol_rec["recommended_weekly_sets"] = int(
                    vol_rec["recommended_weekly_sets"] * coefficient
                )
            
            if "sets_per_session" in vol_rec:
                vol_rec["sets_per_session"] = int(
                    vol_rec["sets_per_session"] * coefficient
                )
        
        self.logger.info(
            f"📊 训练量调整: 水平={fitness_level}, "
            f"系数={coefficient}, "
            f"MEV={volume_data.get('mev', 'N/A')}→{adjusted_data.get('mev', 'N/A')}, "
            f"MAV={volume_data.get('mav', 'N/A')}→{adjusted_data.get('mav', 'N/A')}, "
            f"MRV={volume_data.get('mrv', 'N/A')}→{adjusted_data.get('mrv', 'N/A')}"
        )
        
        return adjusted_data
    
    def apply_periodization_volume(
        self,
        volume_data: Dict[str, Any],
        week_number: int
    ) -> Dict[str, Any]:
        """
        根据周期化原则调整训练量
        
        周期化训练量分配：
        - 第1-2周：使用MAV（最大适应训练量）
        - 第3周：使用MRV（最大可恢复训练量，冲刺周）
        - 第4周：使用MEV（最小有效训练量，减量周）
        
        Args:
            volume_data: 原始训练量数据（包含MEV/MAV/MRV）
            week_number: 当前周数（1-4）
        
        Returns:
            调整后的训练量数据
        """
        # 复制原始数据
        adjusted_data = volume_data.copy()
        
        # 获取MEV/MAV/MRV值
        mev = volume_data.get("mev", 10)
        mav = volume_data.get("mav", 16)
        mrv = volume_data.get("mrv", 22)
        
        # 根据周数确定目标训练量
        if week_number in [1, 2]:
            # 第1-2周：使用MAV（最大适应训练量）
            target_volume = mav
            phase_name = "积累期"
            phase_description = "使用最大适应训练量，诱导肌肥大适应"
        elif week_number == 3:
            # 第3周：使用MRV（最大可恢复训练量，冲刺周）
            target_volume = mrv
            phase_name = "冲刺期"
            phase_description = "使用最大可恢复训练量，达到训练峰值"
        elif week_number == 4:
            # 第4周：使用MEV（最小有效训练量，减量周）
            target_volume = mev
            phase_name = "减量期"
            phase_description = "使用最小有效训练量，促进超量恢复"
        else:
            # 超过4周的情况，循环使用周期
            cycle_week = ((week_number - 1) % 4) + 1
            return self.apply_periodization_volume(volume_data, cycle_week)
        
        # 调整volume_recommendation中的训练量
        if "volume_recommendation" in adjusted_data:
            vol_rec = adjusted_data["volume_recommendation"]
            
            # 调整每周总组数
            if "recommended_weekly_sets" in vol_rec:
                vol_rec["recommended_weekly_sets"] = target_volume
            
            # 调整每次训练组数（假设每周训练2-3次）
            training_frequency = 2  # 默认每周2次
            if "sets_per_session" in vol_rec:
                vol_rec["sets_per_session"] = max(1, target_volume // training_frequency)
            
            # 添加周期化信息
            vol_rec["periodization_phase"] = phase_name
            vol_rec["phase_description"] = phase_description
            vol_rec["target_volume"] = target_volume
        
        self.logger.info(
            f"📊 周期化训练量调整: 第{week_number}周, "
            f"阶段={phase_name}, "
            f"目标训练量={target_volume}组/周, "
            f"MEV={mev}, MAV={mav}, MRV={mrv}"
        )
        
        return adjusted_data
    
    async def _call_volume_calculator(
        self,
        input_data: Dict[str, Any],
        muscle_group: str,
        week_number: int = 1
    ) -> Dict[str, Any]:
        """
        调用muscle_group_volume_calculator工具并根据训练水平和周期调整
        
        Args:
            input_data: 输入数据
            muscle_group: 肌群名称
            week_number: 当前周数（用于周期化调整）
        """
        if not self.tool_registry:
            self.logger.warning("工具注册表未设置，返回默认训练量")
            default_volume = {
                "mev": 10,
                "mav": 16,
                "mrv": 22,
                "volume_recommendation": {
                    "recommended_weekly_sets": 12,
                    "sets_per_session": 4,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
            
            # 根据训练水平调整默认值
            fitness_level = input_data.get("difficulty_level", "intermediate")
            adjusted_volume = self.adjust_volume_by_level(default_volume, fitness_level)
            
            # 根据周期化原则调整训练量
            periodized_volume = self.apply_periodization_volume(adjusted_volume, week_number)
            
            return periodized_volume
        
        try:
            # 构建输入参数
            calculator_input = {
                "user_id": input_data["user_id"],
                "muscle_group": muscle_group,
                "training_goal": input_data["training_goal"],
                "training_frequency_per_week": input_data["training_days_per_week"],
                "current_weekly_sets": None,
                "recovery_capacity": None
            }
            
            # 调用工具
            result = await self.tool_registry.call_tool(
                "muscle_group_volume_calculator",
                calculator_input
            )
            
            if result.get("success"):
                # 根据训练水平调整训练量
                fitness_level = input_data.get("difficulty_level", "intermediate")
                adjusted_result = self.adjust_volume_by_level(result, fitness_level)
                
                # 根据周期化原则调整训练量
                periodized_result = self.apply_periodization_volume(adjusted_result, week_number)
                
                return periodized_result
            else:
                self.logger.error(f"训练量计算失败: {result.get('error')}")
                default_volume = {
                    "mev": 10,
                    "mav": 16,
                    "mrv": 22,
                    "volume_recommendation": {
                        "recommended_weekly_sets": 12,
                        "sets_per_session": 4,
                        "reps_per_set_range": (8, 12),
                        "rest_period_seconds": 90
                    }
                }
                fitness_level = input_data.get("difficulty_level", "intermediate")
                adjusted_volume = self.adjust_volume_by_level(default_volume, fitness_level)
                periodized_volume = self.apply_periodization_volume(adjusted_volume, week_number)
                return periodized_volume
        
        except Exception as e:
            self.logger.error(f"调用muscle_group_volume_calculator失败: {e}", exc_info=True)
            default_volume = {
                "mev": 10,
                "mav": 16,
                "mrv": 22,
                "volume_recommendation": {
                    "recommended_weekly_sets": 12,
                    "sets_per_session": 4,
                    "reps_per_set_range": (8, 12),
                    "rest_period_seconds": 90
                }
            }
            fitness_level = input_data.get("difficulty_level", "intermediate")
            adjusted_volume = self.adjust_volume_by_level(default_volume, fitness_level)
            periodized_volume = self.apply_periodization_volume(adjusted_volume, week_number)
            return periodized_volume
    
    def _detect_deload_days(
        self,
        training_days: List[Dict[str, Any]]
    ) -> List[int]:
        """
        检测需要插入减量日的位置
        
        当连续训练≥3天时，自动插入减量日
        
        Args:
            training_days: 训练日列表
        
        Returns:
            需要设置为减量日的训练日编号列表
        """
        deload_day_numbers = []
        consecutive_training_days = 0
        
        # 按day_number排序
        sorted_days = sorted(training_days, key=lambda d: d["day_number"])
        
        for i, day in enumerate(sorted_days):
            consecutive_training_days += 1
            
            # 当连续训练≥3天时，将第3天设置为减量日
            if consecutive_training_days >= 3:
                deload_day_numbers.append(day["day_number"])
                
                self.logger.info(
                    f"🔄 检测到连续训练3天，"
                    f"将第{day['day_number']}天设置为减量日"
                )
                
                consecutive_training_days = 0  # 重置计数
        
        return deload_day_numbers
    
    def _apply_deload_to_day(
        self,
        training_day: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        将训练日转换为减量日
        
        减量日特点：
        - 训练量减半（50%）
        - 强度降至80%
        - 明确标注减量日及其目的
        - 添加科学依据说明
        
        Args:
            training_day: 原始训练日
        
        Returns:
            调整后的减量日
        """
        # 复制训练日数据
        deload_day = training_day.copy()
        
        # 修改训练日名称
        deload_day["day_name"] = f"{training_day['day_name']} (减量日)"
        
        # 调整每个动作的训练量和强度
        adjusted_exercises = []
        original_total_sets = 0
        adjusted_total_sets = 0
        
        for ex in training_day["exercises"]:
            adjusted_ex = ex.copy()
            
            # 训练量减半（组数减半，向上取整）
            original_sets = ex.get("sets", 3)
            adjusted_sets = max(1, (original_sets + 1) // 2)  # 向上取整
            adjusted_ex["sets"] = adjusted_sets
            
            original_total_sets += original_sets
            adjusted_total_sets += adjusted_sets
            
            # 强度降至80%（通过调整次数范围体现）
            original_reps = ex.get("reps_range", (8, 12))
            if isinstance(original_reps, tuple) and len(original_reps) == 2:
                # 降低次数范围的下限，保持上限
                adjusted_reps = (max(1, int(original_reps[0] * 0.8)), original_reps[1])
                adjusted_ex["reps_range"] = adjusted_reps
            
            # 添加减量日标记
            adjusted_ex["is_deload"] = True
            adjusted_ex["deload_note"] = "减量日：训练量50%，强度80%"
            
            adjusted_exercises.append(adjusted_ex)
        
        # 更新训练日数据
        deload_day["exercises"] = adjusted_exercises
        deload_day["total_sets"] = adjusted_total_sets
        deload_day["is_deload_day"] = True
        
        # 更新预估时长（减半）
        original_duration = training_day.get("estimated_duration_minutes", 60)
        deload_day["estimated_duration_minutes"] = max(30, original_duration // 2)
        
        # 添加减量日说明
        deload_notes = [
            "🔄 减量日：训练量减半（50%），强度降至80%",
            "💡 目的：促进中枢神经系统恢复，避免过度训练",
            "📊 科学依据：连续高强度训练会累积疲劳，减量日有助于超量恢复",
            "✅ 执行要点：保持动作质量，专注于肌肉感受，不追求极限重量",
            "⚠️ 重要：不要跳过减量日，这是训练计划的重要组成部分"
        ]
        
        deload_day["notes"] = deload_notes
        
        self.logger.info(
            f"🔄 应用减量日调整: 第{deload_day['day_number']}天, "
            f"组数 {original_total_sets}→{adjusted_total_sets}, "
            f"时长 {original_duration}→{deload_day['estimated_duration_minutes']}分钟"
        )
        
        return deload_day
    
    def _generate_weekly_program(
        self,
        input_data: Dict[str, Any],
        muscle_group_data: Dict[str, Dict[str, Any]],
        cycle_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        生成周训练计划
        
        Args:
            input_data: 输入数据
            muscle_group_data: 肌群数据
            cycle_info: 训练周期信息
        """
        training_split = input_data["training_split"]
        training_days_per_week = input_data["training_days_per_week"]
        session_duration = input_data.get("session_duration_minutes", 60)
        training_weeks = input_data.get("training_weeks", 4)
        
        # 记录周期信息到日志
        self.logger.info(
            f"📅 生成{training_weeks}周训练计划: "
            f"{training_split}, "
            f"周期={cycle_info['cycle_days']}天, "
            f"模式={cycle_info['training_pattern']}"
        )
        
        # 根据训练分化生成训练日
        training_days = []
        
        if training_split == "full_body":
            # 全身训练：每天训练所有肌群
            for day_num in range(1, training_days_per_week + 1):
                training_day = self._create_full_body_day(
                    day_num,
                    muscle_group_data,
                    input_data
                )
                training_days.append(training_day)
        
        elif training_split == "upper_lower":
            # 上下肢分化：交替训练上肢和下肢
            for day_num in range(1, training_days_per_week + 1):
                if day_num % 2 == 1:
                    # 上肢日
                    training_day = self._create_upper_body_day(
                        day_num,
                        muscle_group_data,
                        input_data
                    )
                else:
                    # 下肢日
                    training_day = self._create_lower_body_day(
                        day_num,
                        muscle_group_data,
                        input_data
                    )
                training_days.append(training_day)
        
        elif training_split == "push_pull_legs":
            # 推拉腿分化
            split_pattern = ["push", "pull", "legs"]
            for day_num in range(1, training_days_per_week + 1):
                pattern_index = (day_num - 1) % 3
                pattern = split_pattern[pattern_index]
                
                if pattern == "push":
                    training_day = self._create_push_day(
                        day_num,
                        muscle_group_data,
                        input_data
                    )
                elif pattern == "pull":
                    training_day = self._create_pull_day(
                        day_num,
                        muscle_group_data,
                        input_data
                    )
                else:  # legs
                    training_day = self._create_legs_day(
                        day_num,
                        muscle_group_data,
                        input_data
                    )
                training_days.append(training_day)
        
        elif training_split == "bro_split":
            # 部位分化：每天一个主要肌群
            muscle_groups = list(muscle_group_data.keys())
            for day_num in range(1, training_days_per_week + 1):
                muscle_index = (day_num - 1) % len(muscle_groups)
                focus_muscle = muscle_groups[muscle_index]
                
                training_day = self._create_single_muscle_day(
                    day_num,
                    focus_muscle,
                    muscle_group_data,
                    input_data
                )
                training_days.append(training_day)
        
        # 检测并应用减量日
        deload_day_numbers = self._detect_deload_days(training_days)
        
        if deload_day_numbers:
            self.logger.info(
                f"🔄 检测到{len(deload_day_numbers)}个减量日: "
                f"{deload_day_numbers}"
            )
            
            # 应用减量日调整
            for i, day in enumerate(training_days):
                if day["day_number"] in deload_day_numbers:
                    training_days[i] = self._apply_deload_to_day(day)
        
        # 计算休息日
        rest_days = [i for i in range(1, 8) if i not in [d["day_number"] for d in training_days]]
        
        # 计算总训练量
        total_weekly_sets = sum(day["total_sets"] for day in training_days)
        
        # 计算肌群分布
        muscle_group_distribution = {}
        for muscle_group in muscle_group_data.keys():
            muscle_sets = sum(
                sum(1 for ex in day["exercises"] if muscle_group in ex.get("primary_muscles", []))
                for day in training_days
            )
            muscle_group_distribution[muscle_group] = muscle_sets
        
        # 统计减量日信息
        deload_days_count = len(deload_day_numbers)
        has_deload_days = deload_days_count > 0
        
        return {
            "week_number": 1,
            "training_days": training_days,
            "rest_days": rest_days,
            "total_weekly_sets": total_weekly_sets,
            "muscle_group_distribution": muscle_group_distribution,
            # 添加周期信息
            "cycle_days": cycle_info["cycle_days"],
            "cycles_per_week": cycle_info["cycles_per_week"],
            "training_pattern": cycle_info["training_pattern"],
            # 添加减量日信息
            "has_deload_days": has_deload_days,
            "deload_days_count": deload_days_count,
            "deload_day_numbers": deload_day_numbers
        }
    
    def _create_full_body_day(
        self,
        day_number: int,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建全身训练日"""
        exercises = []
        total_sets = 0
        
        # 为每个肌群选择1-2个动作
        for muscle_group, data in muscle_group_data.items():
            recommendations = data["exercise_recommendations"].get("recommendations", [])
            volume_data = data["volume_data"]
            
            # 选择前1-2个推荐动作
            selected_exercises = recommendations[:2]
            
            for ex in selected_exercises:
                volume_rec = volume_data.get("volume_recommendation", {})
                sets = min(3, volume_rec.get("sets_per_session", 3))
                
                exercise_in_program = {
                    "exercise_id": ex.get("exercise_id", ""),
                    "name_zh": ex.get("name_zh", ""),
                    "name_en": ex.get("name_en", ""),
                    "category": ex.get("category", ""),
                    "difficulty": ex.get("difficulty_zh") or ex.get("difficulty_en") or "",
                    "sets": sets,
                    "reps_range": volume_rec.get("reps_per_set_range", (8, 12)),
                    "rest_seconds": volume_rec.get("rest_period_seconds", 90),
                    "primary_muscles": ex.get("muscles_primary_zh") or ex.get("primary_muscles") or [],
                    "secondary_muscles": ex.get("muscles_secondary_zh") or ex.get("secondary_muscles") or [],
                    "safety_level": ex.get("safety_level", ""),
                    "safety_notes": ex.get("contraindications_zh", []),
                    "reasoning": ex.get("reasoning", "")
                }
                
                exercises.append(exercise_in_program)
                total_sets += sets
        
        # 生成热身动作（如果启用）
        target_muscles = list(muscle_group_data.keys())
        include_warmup = input_data.get("include_warmup", True)
        warmup_exercises = self._generate_warmup_exercises(
            target_muscles=target_muscles,
            training_split="full_body",
            include_warmup=include_warmup,
            warmup_duration=10
        )
        
        # 生成放松动作（如果启用）
        include_cooldown = input_data.get("include_cooldown", True)
        cooldown_exercises = self._generate_cooldown_exercises(
            target_muscles=target_muscles,
            training_split="full_body",
            include_cooldown=include_cooldown,
            cooldown_duration=10
        )
        
        return {
            "day_number": day_number,
            "day_name": f"全身训练日 {day_number}",
            "focus_muscle_groups": target_muscles,
            "warmup_exercises": warmup_exercises,
            "exercises": exercises,
            "cooldown_exercises": cooldown_exercises,
            "total_sets": total_sets,
            "estimated_duration_minutes": self._estimate_duration(exercises),
            "notes": ["全身训练，注意动作质量", "充分热身和拉伸"],
            "warmup_duration_minutes": 10 if include_warmup else 0,
            "cooldown_duration_minutes": 10 if include_cooldown else 0,
        }
    
    def _create_upper_body_day(
        self,
        day_number: int,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建上肢训练日"""
        upper_body_muscles = ["胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌"]
        return self._create_muscle_group_day(
            day_number,
            f"上肢训练日 {day_number}",
            upper_body_muscles,
            muscle_group_data,
            input_data
        )
    
    def _create_lower_body_day(
        self,
        day_number: int,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建下肢训练日"""
        lower_body_muscles = ["股四头肌", "腘绳肌", "臀大肌", "小腿肌群"]
        return self._create_muscle_group_day(
            day_number,
            f"下肢训练日 {day_number}",
            lower_body_muscles,
            muscle_group_data,
            input_data
        )
    
    def _create_push_day(
        self,
        day_number: int,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建推日"""
        push_muscles = ["胸大肌", "三角肌", "肱三头肌"]
        return self._create_muscle_group_day(
            day_number,
            f"推日 {day_number}",
            push_muscles,
            muscle_group_data,
            input_data
        )
    
    def _create_pull_day(
        self,
        day_number: int,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建拉日"""
        pull_muscles = ["背阔肌", "肱二头肌"]
        return self._create_muscle_group_day(
            day_number,
            f"拉日 {day_number}",
            pull_muscles,
            muscle_group_data,
            input_data
        )
    
    def _create_legs_day(
        self,
        day_number: int,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建腿日"""
        leg_muscles = ["股四头肌", "腘绳肌", "臀大肌"]
        return self._create_muscle_group_day(
            day_number,
            f"腿日 {day_number}",
            leg_muscles,
            muscle_group_data,
            input_data
        )
    
    def _create_single_muscle_day(
        self,
        day_number: int,
        focus_muscle: str,
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建单肌群训练日"""
        return self._create_muscle_group_day(
            day_number,
            f"{focus_muscle}训练日",
            [focus_muscle],
            muscle_group_data,
            input_data
        )
    
    def _create_muscle_group_day(
        self,
        day_number: int,
        day_name: str,
        target_muscles: List[str],
        muscle_group_data: Dict[str, Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建肌群训练日（通用方法）"""
        exercises = []
        total_sets = 0
        
        for muscle_group in target_muscles:
            if muscle_group not in muscle_group_data:
                continue
            
            data = muscle_group_data[muscle_group]
            recommendations = data["exercise_recommendations"].get("recommendations", [])
            volume_data = data["volume_data"]
            
            # 选择前2-3个推荐动作
            selected_exercises = recommendations[:3]
            
            for ex in selected_exercises:
                volume_rec = volume_data.get("volume_recommendation", {})
                sets = volume_rec.get("sets_per_session", 4)
                
                exercise_in_program = {
                    "exercise_id": ex.get("exercise_id", ""),
                    "name_zh": ex.get("name_zh", ""),
                    "name_en": ex.get("name_en", ""),
                    "category": ex.get("category", ""),
                    "difficulty": ex.get("difficulty_zh") or ex.get("difficulty_en") or "",
                    "sets": sets,
                    "reps_range": volume_rec.get("reps_per_set_range", (8, 12)),
                    "rest_seconds": volume_rec.get("rest_period_seconds", 90),
                    "primary_muscles": ex.get("muscles_primary_zh") or ex.get("primary_muscles") or [],
                    "secondary_muscles": ex.get("muscles_secondary_zh") or ex.get("secondary_muscles") or [],
                    "safety_level": ex.get("safety_level", ""),
                    "safety_notes": ex.get("contraindications_zh", []),
                    "reasoning": ex.get("reasoning", "")
                }
                
                exercises.append(exercise_in_program)
                total_sets += sets
        
        # 生成热身动作（如果启用）
        include_warmup = input_data.get("include_warmup", True)
        warmup_exercises = self._generate_warmup_exercises(
            target_muscles=target_muscles,
            training_split=input_data.get("training_split", "full_body"),
            include_warmup=include_warmup,
            warmup_duration=10
        )
        
        # 生成放松动作（如果启用）
        include_cooldown = input_data.get("include_cooldown", True)
        cooldown_exercises = self._generate_cooldown_exercises(
            target_muscles=target_muscles,
            training_split=input_data.get("training_split", "full_body"),
            include_cooldown=include_cooldown,
            cooldown_duration=10
        )
        
        return {
            "day_number": day_number,
            "day_name": day_name,
            "focus_muscle_groups": target_muscles,
            "warmup_exercises": warmup_exercises,
            "exercises": exercises,
            "cooldown_exercises": cooldown_exercises,
            "total_sets": total_sets,
            "estimated_duration_minutes": self._estimate_duration(exercises),
            "notes": [f"专注于{', '.join(target_muscles)}训练", "注意动作质量和肌肉感受"],
            "warmup_duration_minutes": 10 if include_warmup else 0,
            "cooldown_duration_minutes": 10 if include_cooldown else 0,
        }
    
    def _estimate_duration(self, exercises: List[Dict[str, Any]]) -> int:
        """估算训练时长（分钟）"""
        total_minutes = 10  # 热身时间
        
        for ex in exercises:
            sets = ex.get("sets", 3)
            rest_seconds = ex.get("rest_seconds", 90)
            
            # 每组约30秒 + 休息时间
            exercise_time = sets * (30 + rest_seconds) / 60
            total_minutes += exercise_time
        
        total_minutes += 10  # 放松时间
        
        return int(total_minutes)
    
    def _generate_warmup_exercises(
        self,
        target_muscles: List[str],
        training_split: str,
        include_warmup: bool = True,
        warmup_duration: int = 10
    ) -> List[Dict[str, Any]]:
        """
        生成热身动作列表
        
        基于运动学教授和专业教练的视角，从1790个动作中精选热身动作。
        
        Args:
            target_muscles: 目标肌群列表
            training_split: 训练分化类型
            include_warmup: 是否包含热身
            warmup_duration: 热身时长（分钟）
        
        Returns:
            热身动作列表
        """
        if not include_warmup:
            return []
        
        # 确定训练重点
        training_focus = WarmupCooldownSelector.determine_training_focus(
            target_muscles,
            training_split
        )
        
        # 获取热身动作
        warmup_exercises = WarmupCooldownSelector.get_warmup_exercises(
            training_focus=training_focus,
            duration_minutes=warmup_duration,
            include_cardio=True
        )
        
        self.logger.info(
            f"🔥 生成热身动作: 训练重点={training_focus.value}, "
            f"动作数={len(warmup_exercises)}, 时长={warmup_duration}分钟"
        )
        
        return warmup_exercises
    
    def _generate_cooldown_exercises(
        self,
        target_muscles: List[str],
        training_split: str,
        include_cooldown: bool = True,
        cooldown_duration: int = 10
    ) -> List[Dict[str, Any]]:
        """
        生成放松动作列表
        
        基于运动学教授和专业教练的视角，从1790个动作中精选放松动作。
        
        Args:
            target_muscles: 目标肌群列表
            training_split: 训练分化类型
            include_cooldown: 是否包含放松
            cooldown_duration: 放松时长（分钟）
        
        Returns:
            放松动作列表
        """
        if not include_cooldown:
            return []
        
        # 确定训练重点
        training_focus = WarmupCooldownSelector.determine_training_focus(
            target_muscles,
            training_split
        )
        
        # 获取放松动作
        cooldown_exercises = WarmupCooldownSelector.get_cooldown_exercises(
            training_focus=training_focus,
            duration_minutes=cooldown_duration
        )
        
        self.logger.info(
            f"🧘 生成放松动作: 训练重点={training_focus.value}, "
            f"动作数={len(cooldown_exercises)}, 时长={cooldown_duration}分钟"
        )
        
        return cooldown_exercises
    
    def _analyze_program_balance(
        self,
        weekly_program: Dict[str, Any],
        muscle_group_data: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析计划平衡性"""
        training_days = weekly_program["training_days"]
        muscle_distribution = weekly_program["muscle_group_distribution"]
        
        # 1. 分析肌群覆盖
        muscle_group_coverage = {}
        for muscle_group, sets in muscle_distribution.items():
            volume_data = muscle_group_data.get(muscle_group, {}).get("volume_data", {})
            mev = volume_data.get("mev", 10)
            mav = volume_data.get("mav", 16)
            
            if sets >= mav:
                coverage = "充分"
            elif sets >= mev:
                coverage = "适中"
            else:
                coverage = "不足"
            
            muscle_group_coverage[muscle_group] = coverage
        
        # 2. 分析动作模式平衡
        movement_pattern_balance = {}
        for day in training_days:
            for ex in day["exercises"]:
                category = ex.get("category", "Unknown")
                movement_pattern_balance[category] = movement_pattern_balance.get(category, 0) + 1
        
        # 3. 计算推拉比例
        push_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if any(m in ["胸大肌", "三角肌", "肱三头肌"] for m in ex.get("primary_muscles", []))
        )
        pull_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if any(m in ["背阔肌", "肱二头肌"] for m in ex.get("primary_muscles", []))
        )
        
        if pull_count > 0:
            push_pull_ratio = f"{push_count}:{pull_count}"
        else:
            push_pull_ratio = f"{push_count}:0"
        
        # 4. 计算复合/孤立比例
        compound_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if "复合" in ex.get("category", "") or len(ex.get("primary_muscles", [])) > 1
        )
        isolation_count = sum(
            1 for day in training_days
            for ex in day["exercises"]
            if "孤立" in ex.get("category", "")
        )
        
        if isolation_count > 0:
            compound_isolation_ratio = f"{compound_count}:{isolation_count}"
        else:
            compound_isolation_ratio = f"{compound_count}:0"
        
        # 5. 计算平衡评分
        balance_score = 100.0
        
        # 肌群覆盖不足扣分
        insufficient_count = sum(1 for c in muscle_group_coverage.values() if c == "不足")
        balance_score -= insufficient_count * 10
        
        # 推拉比例不平衡扣分
        if push_count > 0 and pull_count > 0:
            ratio = push_count / pull_count
            if ratio < 0.7 or ratio > 1.5:
                balance_score -= 10
        
        balance_score = max(0.0, balance_score)
        
        # 6. 生成建议
        recommendations = []
        
        for muscle_group, coverage in muscle_group_coverage.items():
            if coverage == "不足":
                recommendations.append(f"增加{muscle_group}的训练量")
        
        if push_count > pull_count * 1.5:
            recommendations.append("增加拉类动作，平衡推拉比例")
        elif pull_count > push_count * 1.5:
            recommendations.append("增加推类动作，平衡推拉比例")
        
        if compound_count < isolation_count:
            recommendations.append("增加复合动作比例，提高训练效率")
        
        return {
            "muscle_group_coverage": muscle_group_coverage,
            "movement_pattern_balance": movement_pattern_balance,
            "push_pull_ratio": push_pull_ratio,
            "compound_isolation_ratio": compound_isolation_ratio,
            "balance_score": balance_score,
            "recommendations": recommendations
        }
    
    async def _perform_safety_assessment(
        self,
        weekly_program: Dict[str, Any],
        input_data: Dict[str, Any],
        tools_called: List[str]
    ) -> Dict[str, Any]:
        """进行安全评估"""
        if not self.tool_registry:
            self.logger.warning("工具注册表未设置，跳过安全评估")
            return {
                "overall_risk_level": "LOW",
                "high_risk_exercises": [],
                "contraindications_found": 0,
                "safety_recommendations": [],
                "medical_consultation_needed": False
            }
        
        try:
            # 收集所有动作ID
            exercise_ids = []
            for day in weekly_program["training_days"]:
                for ex in day["exercises"]:
                    exercise_id = ex.get("exercise_id")
                    if exercise_id and exercise_id not in exercise_ids:
                        exercise_ids.append(exercise_id)
            
            if not exercise_ids:
                return {
                    "overall_risk_level": "LOW",
                    "high_risk_exercises": [],
                    "contraindications_found": 0,
                    "safety_recommendations": [],
                    "medical_consultation_needed": False
                }
            
            # 调用contraindications_checker
            checker_input = {
                "user_id": input_data["user_id"],
                "exercise_ids": exercise_ids,
                "health_conditions": input_data.get("injury_history"),
                "include_recommendations": True,
                "strict_mode": False
            }
            
            result = await self.tool_registry.call_tool(
                "contraindications_checker",
                checker_input
            )
            
            tools_called.append("contraindications_checker")
            
            if result.get("success"):
                # 提取高风险动作
                high_risk_exercises = [
                    ex["exercise_name_zh"]
                    for ex in result.get("exercise_results", [])
                    if ex.get("max_risk_level") in ["HIGH", "CRITICAL"]
                ]
                
                # 提取安全建议
                safety_recommendations = result.get("overall_assessment", {}).get("recommendations", [])
                
                return {
                    "overall_risk_level": result.get("overall_assessment", {}).get("risk_level", "LOW"),
                    "high_risk_exercises": high_risk_exercises,
                    "contraindications_found": result.get("exercises_with_contraindications", 0),
                    "safety_recommendations": safety_recommendations,
                    "medical_consultation_needed": result.get("overall_assessment", {}).get("risk_level") in ["HIGH", "CRITICAL"]
                }
            else:
                self.logger.error(f"安全评估失败: {result.get('error')}")
                return {
                    "overall_risk_level": "MODERATE",
                    "high_risk_exercises": [],
                    "contraindications_found": 0,
                    "safety_recommendations": ["无法完成安全评估，建议谨慎训练"],
                    "medical_consultation_needed": False
                }
        
        except Exception as e:
            self.logger.error(f"调用contraindications_checker失败: {e}", exc_info=True)
            return {
                "overall_risk_level": "MODERATE",
                "high_risk_exercises": [],
                "contraindications_found": 0,
                "safety_recommendations": ["安全评估出错，建议谨慎训练"],
                "medical_consultation_needed": False
            }
    
    def _generate_execution_guidelines(
        self,
        input_data: Dict[str, Any],
        weekly_program: Dict[str, Any],
        program_balance: Dict[str, Any],
        safety_assessment: Dict[str, Any],
        applicable_standard: Dict[str, Any]
    ) -> List[str]:
        """生成执行建议（包含标准引用）"""
        guidelines = []
        
        # 添加科学依据说明
        guidelines.append(
            f"📚 科学依据：本计划基于{applicable_standard['standard_name']}制定"
        )
        guidelines.append(
            f"   {applicable_standard['application_reason']}"
        )
        
        # 基于训练目标的建议
        training_goal = input_data["training_goal"]
        if training_goal == "strength":
            guidelines.append("力量训练：注重动作质量和渐进超负荷")
        elif training_goal == "hypertrophy":
            guidelines.append("肌肥大训练：保持肌肉张力和代谢压力")
        elif training_goal == "endurance":
            guidelines.append("耐力训练：控制休息时间，保持训练密度")
        
        # 基于训练周期的建议
        cycle_days = weekly_program.get("cycle_days", 7)
        training_pattern = weekly_program.get("training_pattern", "")
        
        if cycle_days <= 4:
            guidelines.append(
                f"训练周期为{cycle_days}天（{training_pattern}），"
                f"注意在每个周期结束后充分休息恢复"
            )
        
        if training_pattern == "练三休一":
            guidelines.append("推拉腿分化：每3天训练后休息1天，确保肌群充分恢复")
        elif training_pattern == "练六休一":
            guidelines.append("高频训练：连续6天训练后休息1天，注意监控疲劳水平")
        elif training_pattern == "练二休一":
            guidelines.append("上下肢分化：每2天训练后休息1天，平衡训练强度")
        
        # 减量日相关建议
        has_deload_days = weekly_program.get("has_deload_days", False)
        deload_days_count = weekly_program.get("deload_days_count", 0)
        
        if has_deload_days:
            guidelines.append(
                f"🔄 减量日管理：本计划包含{deload_days_count}个减量日，"
                f"用于促进中枢神经系统恢复"
            )
            guidelines.append(
                "减量日执行要点：训练量减半（50%），强度降至80%，"
                "专注于动作质量和肌肉感受"
            )
            guidelines.append(
                "⚠️ 重要：不要跳过减量日，这是避免过度训练和促进超量恢复的关键"
            )
        
        # 通用建议
        guidelines.extend([
            "每次训练前进行充分热身（5-10分钟）",
            "训练后进行拉伸放松（5-10分钟）",
            "保持训练日志，记录组数、次数和感受",
            "根据身体反馈调整训练强度"
        ])
        
        return guidelines
    
    def _generate_important_notes(
        self,
        input_data: Dict[str, Any],
        safety_assessment: Dict[str, Any],
        program_balance: Dict[str, Any],
        weekly_program: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """生成注意事项"""
        notes = []
        
        # 安全相关
        if safety_assessment["overall_risk_level"] in ["HIGH", "CRITICAL"]:
            notes.append("⚠️ 存在高风险动作，建议在专业人士指导下进行")
        
        if safety_assessment["medical_consultation_needed"]:
            notes.append("⚠️ 建议在开始训练前咨询医疗专业人士")
        
        # 平衡性相关
        if program_balance["balance_score"] < 70:
            notes.append("注意：计划平衡性有待改善，建议调整动作选择")
        
        # 减量日相关注意事项
        if weekly_program:
            has_deload_days = weekly_program.get("has_deload_days", False)
            deload_day_numbers = weekly_program.get("deload_day_numbers", [])
            
            if has_deload_days:
                notes.append(
                    f"🔄 减量日安排：第{', '.join(map(str, deload_day_numbers))}天为减量日"
                )
                notes.append(
                    "💡 减量日科学依据：连续高强度训练会累积中枢神经系统疲劳，"
                    "减量日有助于神经系统恢复和超量恢复"
                )
                notes.append(
                    "📊 研究表明：适当的减量日可以提高训练效果，"
                    "降低过度训练风险，促进长期进步"
                )
        
        # 通用注意事项
        notes.extend([
            "如有不适立即停止训练",
            "保证充足睡眠和营养摄入",
            "定期评估训练进展"
        ])
        
        return notes
