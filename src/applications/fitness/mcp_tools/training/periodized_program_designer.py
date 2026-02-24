"""
周期化程序设计器 MCP工具

设计多周期、多阶段的训练计划，支持多种周期化模型
包括线性周期化、波动周期化、块状周期化等

功能特性：
- 支持多种周期化模型（Linear, DUP, Block, Conjugate）
- 根据用户水平和目标选择合适的周期化方案
- 设计多周期训练计划（4-12周）
- 包含适应期、积累期、强化期、减量期
- 自动调整训练强度和容量

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-15
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
import logging

from ..base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举类型定义
# =============================================================================

class PeriodizationModel(str, Enum):
    """周期化模型"""
    LINEAR = "linear"  # 线性周期化
    DUP = "dup"  # 每日波动周期化
    BLOCK = "block"  # 块状周期化
    CONJUGATE = "conjugate"  # 共轭周期化


class TrainingPhase(str, Enum):
    """训练阶段"""
    ADAPTATION = "adaptation"  # 适应期
    ACCUMULATION = "accumulation"  # 积累期
    INTENSIFICATION = "intensification"  # 强化期
    REALIZATION = "realization"  # 实现期
    DELOAD = "deload"  # 减量期


from ...types.enums import TrainingGoal, DifficultyLevel


# =============================================================================
# 输入Schema定义
# =============================================================================

class PeriodizedProgramDesignerInput(BaseModel):
    """周期化程序设计器输入Schema"""
    
    # 用户信息
    user_id: str = Field(..., description="用户ID")
    
    # 训练目标和水平
    training_goal: TrainingGoal = Field(..., description="训练目标")
    difficulty_level: DifficultyLevel = Field(..., description="难度等级")
    
    # 周期化设置
    periodization_model: Optional[PeriodizationModel] = Field(
        None, 
        description="周期化模型（可选，不指定则自动选择）"
    )
    program_duration_weeks: int = Field(
        ..., 
        ge=4, 
        le=16, 
        description="计划总周数（4-16周）"
    )
    training_days_per_week: int = Field(..., ge=2, le=6, description="每星期训练天数")
    
    # 器械和限制
    available_equipment: List[str] = Field(..., description="可用器械列表")
    injury_history: Optional[List[str]] = Field(None, description="损伤历史（可选）")
    
    # 目标肌群（可选）
    target_muscle_groups: Optional[List[str]] = Field(None, description="目标肌群列表（可选）")
    
    # 高级设置
    include_deload_weeks: bool = Field(True, description="是否包含减量周")
    auto_progression: bool = Field(True, description="是否自动渐进超负荷")


# =============================================================================
# 输出Schema定义
# =============================================================================

class PhaseDetails(BaseModel):
    """阶段详情"""
    phase_name: str
    phase_type: TrainingPhase
    week_range: tuple[int, int]
    duration_weeks: int
    
    # 训练参数
    intensity_range: tuple[int, int]  # 强度范围（%1RM）
    volume_multiplier: float  # 容量倍数
    sets_per_exercise_range: tuple[int, int]
    reps_per_set_range: tuple[int, int]
    rest_seconds_range: tuple[int, int]
    
    # 阶段目标
    phase_goals: List[str]
    key_focus: str
    
    # 注意事项
    notes: List[str]


class WeekPlan(BaseModel):
    """周计划"""
    week_number: int
    phase_type: TrainingPhase
    phase_name: str
    
    # 训练参数
    training_days: int
    intensity_percentage: int  # 平均强度（%1RM）
    volume_sets: int  # 总组数
    
    # 周目标
    week_goals: List[str]
    
    # 是否减量周
    is_deload: bool


class PeriodizedProgram(BaseModel):
    """周期化计划"""
    program_name: str
    periodization_model: PeriodizationModel
    total_weeks: int
    
    # 阶段划分
    phases: List[PhaseDetails]
    
    # 周计划
    weekly_plans: List[WeekPlan]
    
    # 渐进策略
    progression_strategy: Dict[str, Any]


class PeriodizedProgramDesignerOutput(BaseModel):
    """周期化程序设计器输出Schema"""
    
    success: bool
    tool_name: str
    user_id: str
    
    # 计划概览
    program_overview: Dict[str, Any]
    
    # 周期化计划
    periodized_program: PeriodizedProgram
    
    # 执行建议
    execution_guidelines: List[str]
    
    # 注意事项
    important_notes: List[str]
    
    # 元数据
    execution_time_ms: float
    confidence_score: float


# =============================================================================
# 周期化程序设计器类
# =============================================================================

class PeriodizedProgramDesigner(BaseMCPTool):
    """
    周期化程序设计器
    
    设计多周期、多阶段的训练计划
    支持多种周期化模型和自动渐进策略
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
        初始化周期化程序设计器
        
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
        return "periodized_program_designer"
    
    def get_description(self) -> str:
        return "周期化程序设计器 - 设计多周期、多阶段的训练计划，支持多种周期化模型"
    
    def get_category(self) -> str:
        return "training"
    
    def get_input_schema(self) -> type[BaseModel]:
        return PeriodizedProgramDesignerInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return PeriodizedProgramDesignerOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 3000.0  # 3秒
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return [
            "neo4j",
            "qdrant",
            "three_layer_engine"
        ]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行周期化程序设计
        
        流程：
        1. 选择周期化模型（如果未指定）
        2. 划分训练阶段
        3. 生成周计划
        4. 设计渐进策略
        5. 生成执行建议
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 选择周期化模型
            periodization_model = self._select_periodization_model(input_data)
            
            # Step 2: 划分训练阶段
            phases = self._design_training_phases(
                periodization_model,
                input_data
            )
            
            # Step 3: 生成周计划
            weekly_plans = self._generate_weekly_plans(
                phases,
                input_data
            )
            
            # Step 4: 设计渐进策略
            progression_strategy = self._design_progression_strategy(
                periodization_model,
                input_data
            )
            
            # Step 5: 生成执行建议
            execution_guidelines = self._generate_execution_guidelines(
                periodization_model,
                input_data
            )
            
            # Step 6: 生成注意事项
            important_notes = self._generate_important_notes(
                periodization_model,
                input_data
            )
            
            # 构建周期化计划
            periodized_program = {
                "program_name": self._generate_program_name(periodization_model, input_data),
                "periodization_model": periodization_model,
                "total_weeks": input_data["program_duration_weeks"],
                "phases": phases,
                "weekly_plans": weekly_plans,
                "progression_strategy": progression_strategy
            }
            
            # 生成计划概览
            program_overview = {
                "periodization_model": periodization_model,
                "training_goal": input_data["training_goal"],
                "difficulty_level": input_data["difficulty_level"],
                "total_weeks": input_data["program_duration_weeks"],
                "training_days_per_week": input_data["training_days_per_week"],
                "total_phases": len(phases),
                "includes_deload": input_data.get("include_deload_weeks", True)
            }
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": self.get_name(),
                "user_id": input_data["user_id"],
                "program_overview": program_overview,
                "periodized_program": periodized_program,
                "execution_guidelines": execution_guidelines,
                "important_notes": important_notes,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 88.0
            }
            
            self.logger.info(
                f"✅ 周期化程序设计完成: {periodization_model}, "
                f"{input_data['program_duration_weeks']}周, "
                f"{len(phases)}个阶段"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 周期化程序设计失败: {e}", exc_info=True)
            raise
    
    def _select_periodization_model(
        self,
        input_data: Dict[str, Any]
    ) -> PeriodizationModel:
        """
        选择周期化模型
        
        规则：
        - beginner: Linear Periodization（简单、结构化）
        - intermediate: DUP（提供变化、防止停滞）
        - advanced: Block或Conjugate（需要高级编排）
        """
        # 如果用户指定了模型，直接使用
        if input_data.get("periodization_model"):
            return input_data["periodization_model"]
        
        # 否则根据训练水平自动选择
        difficulty_level = input_data["difficulty_level"]
        training_goal = input_data["training_goal"]
        
        if difficulty_level == "beginner":
            return PeriodizationModel.LINEAR
        
        elif difficulty_level == "intermediate":
            return PeriodizationModel.DUP
        
        elif difficulty_level == "advanced":
            # 高级训练者根据目标选择
            if training_goal == "power":
                return PeriodizationModel.CONJUGATE
            else:
                return PeriodizationModel.BLOCK
        
        else:
            # 默认线性周期化
            return PeriodizationModel.LINEAR
    
    def _design_training_phases(
        self,
        periodization_model: PeriodizationModel,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        划分训练阶段
        
        不同周期化模型有不同的阶段划分：
        - Linear: 适应期 → 肥大期 → 力量期 → 峰值期 → 减量期
        - DUP: 每周波动，无明显阶段
        - Block: 积累块 → 强化块 → 实现块
        - Conjugate: 最大力量日 + 动态力量日（持续）
        """
        total_weeks = input_data["program_duration_weeks"]
        include_deload = input_data.get("include_deload_weeks", True)
        
        phases = []
        
        if periodization_model == PeriodizationModel.LINEAR:
            phases = self._design_linear_phases(total_weeks, include_deload, input_data)
        
        elif periodization_model == PeriodizationModel.DUP:
            phases = self._design_dup_phases(total_weeks, include_deload, input_data)
        
        elif periodization_model == PeriodizationModel.BLOCK:
            phases = self._design_block_phases(total_weeks, include_deload, input_data)
        
        elif periodization_model == PeriodizationModel.CONJUGATE:
            phases = self._design_conjugate_phases(total_weeks, include_deload, input_data)
        
        return phases
    
    def _design_linear_phases(
        self,
        total_weeks: int,
        include_deload: bool,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """设计线性周期化阶段"""
        phases = []
        current_week = 1
        
        # 阶段1: 适应期（2周）
        if total_weeks >= 8:
            adaptation_weeks = 2
            phases.append({
                "phase_name": "适应期",
                "phase_type": TrainingPhase.ADAPTATION,
                "week_range": (current_week, current_week + adaptation_weeks - 1),
                "duration_weeks": adaptation_weeks,
                "intensity_range": (50, 60),
                "volume_multiplier": 0.7,
                "sets_per_exercise_range": (2, 3),
                "reps_per_set_range": (12, 15),
                "rest_seconds_range": (60, 90),
                "phase_goals": [
                    "建立动作模式",
                    "提高肌肉耐力",
                    "适应训练负荷"
                ],
                "key_focus": "动作质量和技术",
                "notes": [
                    "重点学习正确动作模式",
                    "不追求大重量",
                    "充分感受目标肌群"
                ]
            })
            current_week += adaptation_weeks
        
        # 阶段2: 肥大期（3-4周）
        hypertrophy_weeks = min(4, (total_weeks - current_week + 1) // 2)
        if hypertrophy_weeks > 0:
            phases.append({
                "phase_name": "肥大期",
                "phase_type": TrainingPhase.ACCUMULATION,
                "week_range": (current_week, current_week + hypertrophy_weeks - 1),
                "duration_weeks": hypertrophy_weeks,
                "intensity_range": (65, 75),
                "volume_multiplier": 1.0,
                "sets_per_exercise_range": (3, 4),
                "reps_per_set_range": (8, 12),
                "rest_seconds_range": (90, 120),
                "phase_goals": [
                    "增加肌肉体积",
                    "提高代谢压力",
                    "积累训练容量"
                ],
                "key_focus": "肌肉泵感和张力",
                "notes": [
                    "保持肌肉持续张力",
                    "控制离心阶段",
                    "追求肌肉泵感"
                ]
            })
            current_week += hypertrophy_weeks
        
        # 阶段3: 力量期（3-4周）
        strength_weeks = total_weeks - current_week + 1
        if include_deload:
            strength_weeks -= 1
        
        if strength_weeks > 0:
            phases.append({
                "phase_name": "力量期",
                "phase_type": TrainingPhase.INTENSIFICATION,
                "week_range": (current_week, current_week + strength_weeks - 1),
                "duration_weeks": strength_weeks,
                "intensity_range": (80, 90),
                "volume_multiplier": 0.7,
                "sets_per_exercise_range": (3, 5),
                "reps_per_set_range": (4, 6),
                "rest_seconds_range": (180, 240),
                "phase_goals": [
                    "提高最大力量",
                    "增强神经募集",
                    "突破力量平台"
                ],
                "key_focus": "爆发力和速度",
                "notes": [
                    "注重动作速度",
                    "充分休息恢复",
                    "避免过度训练"
                ]
            })
            current_week += strength_weeks
        
        # 阶段4: 减量期（1周）
        if include_deload:
            phases.append({
                "phase_name": "减量期",
                "phase_type": TrainingPhase.DELOAD,
                "week_range": (current_week, current_week),
                "duration_weeks": 1,
                "intensity_range": (50, 60),
                "volume_multiplier": 0.5,
                "sets_per_exercise_range": (2, 3),
                "reps_per_set_range": (8, 10),
                "rest_seconds_range": (90, 120),
                "phase_goals": [
                    "促进恢复",
                    "消除疲劳",
                    "准备下一周期"
                ],
                "key_focus": "主动恢复",
                "notes": [
                    "降低训练强度和容量",
                    "保持动作质量",
                    "注重睡眠和营养"
                ]
            })
        
        return phases
    
    def _design_dup_phases(
        self,
        total_weeks: int,
        include_deload: bool,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """设计每日波动周期化阶段"""
        phases = []
        
        # DUP模型：整个周期作为一个阶段，每天强度波动
        training_weeks = total_weeks - (1 if include_deload else 0)
        
        phases.append({
            "phase_name": "每日波动训练期",
            "phase_type": TrainingPhase.ACCUMULATION,
            "week_range": (1, training_weeks),
            "duration_weeks": training_weeks,
            "intensity_range": (65, 85),
            "volume_multiplier": 1.0,
            "sets_per_exercise_range": (3, 5),
            "reps_per_set_range": (5, 12),
            "rest_seconds_range": (90, 180),
            "phase_goals": [
                "同时发展多种素质",
                "防止训练停滞",
                "提供训练变化"
            ],
            "key_focus": "每日强度波动",
            "notes": [
                "每天训练不同强度区间",
                "肥大日：70-80% 1RM, 8-12次",
                "力量日：85-90% 1RM, 3-5次",
                "爆发日：30-60% 1RM, 快速爆发"
            ]
        })
        
        # 减量周
        if include_deload:
            phases.append({
                "phase_name": "减量期",
                "phase_type": TrainingPhase.DELOAD,
                "week_range": (total_weeks, total_weeks),
                "duration_weeks": 1,
                "intensity_range": (50, 60),
                "volume_multiplier": 0.5,
                "sets_per_exercise_range": (2, 3),
                "reps_per_set_range": (8, 10),
                "rest_seconds_range": (90, 120),
                "phase_goals": [
                    "促进恢复",
                    "消除疲劳"
                ],
                "key_focus": "主动恢复",
                "notes": [
                    "降低训练强度和容量"
                ]
            })
        
        return phases
    
    def _design_block_phases(
        self,
        total_weeks: int,
        include_deload: bool,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """设计块状周期化阶段"""
        phases = []
        current_week = 1
        
        # 计算每个块的周数
        available_weeks = total_weeks - (1 if include_deload else 0)
        block_weeks = available_weeks // 3
        
        # 块1: 积累块（高容量，中等强度）
        phases.append({
            "phase_name": "积累块",
            "phase_type": TrainingPhase.ACCUMULATION,
            "week_range": (current_week, current_week + block_weeks - 1),
            "duration_weeks": block_weeks,
            "intensity_range": (60, 75),
            "volume_multiplier": 1.2,
            "sets_per_exercise_range": (4, 5),
            "reps_per_set_range": (8, 12),
            "rest_seconds_range": (90, 120),
            "phase_goals": [
                "积累训练容量",
                "增加肌肉体积",
                "建立工作能力"
            ],
            "key_focus": "高容量训练",
            "notes": [
                "专注于积累训练量",
                "保持中等强度",
                "注重恢复"
            ]
        })
        current_week += block_weeks
        
        # 块2: 强化块（中等容量，高强度）
        phases.append({
            "phase_name": "强化块",
            "phase_type": TrainingPhase.INTENSIFICATION,
            "week_range": (current_week, current_week + block_weeks - 1),
            "duration_weeks": block_weeks,
            "intensity_range": (80, 90),
            "volume_multiplier": 0.8,
            "sets_per_exercise_range": (3, 4),
            "reps_per_set_range": (4, 6),
            "rest_seconds_range": (180, 240),
            "phase_goals": [
                "提高最大力量",
                "增强神经适应",
                "准备峰值表现"
            ],
            "key_focus": "高强度训练",
            "notes": [
                "降低容量，提高强度",
                "充分休息",
                "注重动作速度"
            ]
        })
        current_week += block_weeks
        
        # 块3: 实现块（低容量，极高强度）
        realization_weeks = available_weeks - (block_weeks * 2)
        if realization_weeks > 0:
            phases.append({
                "phase_name": "实现块",
                "phase_type": TrainingPhase.REALIZATION,
                "week_range": (current_week, current_week + realization_weeks - 1),
                "duration_weeks": realization_weeks,
                "intensity_range": (90, 100),
                "volume_multiplier": 0.5,
                "sets_per_exercise_range": (2, 3),
                "reps_per_set_range": (1, 3),
                "rest_seconds_range": (240, 300),
                "phase_goals": [
                    "实现峰值力量",
                    "测试最大力量",
                    "展现训练成果"
                ],
                "key_focus": "峰值表现",
                "notes": [
                    "极低容量，极高强度",
                    "完全恢复",
                    "准备测试"
                ]
            })
            current_week += realization_weeks
        
        # 减量周
        if include_deload:
            phases.append({
                "phase_name": "减量期",
                "phase_type": TrainingPhase.DELOAD,
                "week_range": (total_weeks, total_weeks),
                "duration_weeks": 1,
                "intensity_range": (50, 60),
                "volume_multiplier": 0.5,
                "sets_per_exercise_range": (2, 3),
                "reps_per_set_range": (8, 10),
                "rest_seconds_range": (90, 120),
                "phase_goals": [
                    "促进恢复"
                ],
                "key_focus": "主动恢复",
                "notes": [
                    "降低训练负荷"
                ]
            })
        
        return phases
    
    def _design_conjugate_phases(
        self,
        total_weeks: int,
        include_deload: bool,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """设计共轭周期化阶段"""
        phases = []
        
        # Conjugate模型：整个周期作为一个阶段，每星期包含不同训练日
        training_weeks = total_weeks - (1 if include_deload else 0)
        
        phases.append({
            "phase_name": "共轭训练期",
            "phase_type": TrainingPhase.ACCUMULATION,
            "week_range": (1, training_weeks),
            "duration_weeks": training_weeks,
            "intensity_range": (60, 95),
            "volume_multiplier": 1.0,
            "sets_per_exercise_range": (3, 5),
            "reps_per_set_range": (1, 8),
            "rest_seconds_range": (120, 240),
            "phase_goals": [
                "同时发展最大力量和爆发力",
                "频繁变换训练刺激",
                "防止适应和停滞"
            ],
            "key_focus": "最大力量日 + 动态力量日",
            "notes": [
                "最大力量日：90-100% 1RM, 1-3次",
                "动态力量日：60-75% 1RM, 快速爆发",
                "每周轮换主要动作变式",
                "高频率训练（每星期2-3次/肌群）"
            ]
        })
        
        # 减量周
        if include_deload:
            phases.append({
                "phase_name": "减量期",
                "phase_type": TrainingPhase.DELOAD,
                "week_range": (total_weeks, total_weeks),
                "duration_weeks": 1,
                "intensity_range": (50, 60),
                "volume_multiplier": 0.5,
                "sets_per_exercise_range": (2, 3),
                "reps_per_set_range": (8, 10),
                "rest_seconds_range": (90, 120),
                "phase_goals": [
                    "促进恢复"
                ],
                "key_focus": "主动恢复",
                "notes": [
                    "降低训练负荷"
                ]
            })
        
        return phases
    
    def _generate_weekly_plans(
        self,
        phases: List[Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成周计划"""
        weekly_plans = []
        
        for phase in phases:
            week_start, week_end = phase["week_range"]
            
            for week_num in range(week_start, week_end + 1):
                # 计算该周在阶段中的进度
                phase_progress = (week_num - week_start) / phase["duration_weeks"]
                
                # 根据进度调整强度（线性增长）
                intensity_min, intensity_max = phase["intensity_range"]
                week_intensity = int(intensity_min + (intensity_max - intensity_min) * phase_progress)
                
                # 计算训练量
                base_sets = input_data["training_days_per_week"] * 4  # 每天约4组
                volume_sets = int(base_sets * phase["volume_multiplier"])
                
                # 判断是否减量周
                is_deload = phase["phase_type"] == TrainingPhase.DELOAD
                
                weekly_plan = {
                    "week_number": week_num,
                    "phase_type": phase["phase_type"],
                    "phase_name": phase["phase_name"],
                    "training_days": input_data["training_days_per_week"],
                    "intensity_percentage": week_intensity,
                    "volume_sets": volume_sets,
                    "week_goals": self._generate_week_goals(phase, week_num, week_start),
                    "is_deload": is_deload
                }
                
                weekly_plans.append(weekly_plan)
        
        return weekly_plans
    
    def _generate_week_goals(
        self,
        phase: Dict[str, Any],
        week_num: int,
        phase_start_week: int
    ) -> List[str]:
        """生成训练周期目标"""
        week_in_phase = week_num - phase_start_week + 1
        
        goals = []
        
        if phase["phase_type"] == TrainingPhase.ADAPTATION:
            goals.append(f"第{week_in_phase}训练周期：掌握基本动作模式")
        
        elif phase["phase_type"] == TrainingPhase.ACCUMULATION:
            goals.append(f"第{week_in_phase}训练周期：积累训练容量")
        
        elif phase["phase_type"] == TrainingPhase.INTENSIFICATION:
            goals.append(f"第{week_in_phase}训练周期：提高训练强度")
        
        elif phase["phase_type"] == TrainingPhase.REALIZATION:
            goals.append(f"第{week_in_phase}训练周期：实现峰值表现")
        
        elif phase["phase_type"] == TrainingPhase.DELOAD:
            goals.append("减量恢复训练周期")
        
        # 添加阶段目标
        goals.extend(phase["phase_goals"][:2])
        
        return goals
    
    def _design_progression_strategy(
        self,
        periodization_model: PeriodizationModel,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """设计渐进策略"""
        strategy = {
            "model": periodization_model,
            "auto_progression": input_data.get("auto_progression", True),
            "progression_methods": [],
            "progression_rules": []
        }
        
        if periodization_model == PeriodizationModel.LINEAR:
            strategy["progression_methods"] = [
                "每训练周期增加2.5-5%强度",
                "保持次数不变",
                "逐步降低容量"
            ]
            strategy["progression_rules"] = [
                "如果能完成所有组数和次数，下一训练周期增加重量",
                "如果无法完成，保持当前重量再练一训练周期",
                "连续两训练周期无法完成，考虑减量"
            ]
        
        elif periodization_model == PeriodizationModel.DUP:
            strategy["progression_methods"] = [
                "每训练周期在相同强度日增加重量或次数",
                "保持每日强度波动模式",
                "逐步提高各强度区间的负荷"
            ]
            strategy["progression_rules"] = [
                "肥大日：能完成12次则增加重量",
                "力量日：能完成5次则增加重量",
                "爆发日：保持速度质量，逐步增加负荷"
            ]
        
        elif periodization_model == PeriodizationModel.BLOCK:
            strategy["progression_methods"] = [
                "每个块内逐步增加负荷",
                "块与块之间降低容量、提高强度",
                "最后一块实现峰值"
            ]
            strategy["progression_rules"] = [
                "积累块：每训练周期增加1-2组",
                "强化块：每训练周期增加2.5-5%强度",
                "实现块：测试最大力量"
            ]
        
        elif periodization_model == PeriodizationModel.CONJUGATE:
            strategy["progression_methods"] = [
                "每训练周期轮换主要动作变式",
                "保持最大力量日和动态力量日的强度",
                "通过动作变换提供新刺激"
            ]
            strategy["progression_rules"] = [
                "最大力量日：每3训练周期尝试新的1-3RM",
                "动态力量日：保持速度，逐步增加负荷",
                "辅助动作：每训练周期增加重量或次数"
            ]
        
        return strategy
    
    def _generate_execution_guidelines(
        self,
        periodization_model: PeriodizationModel,
        input_data: Dict[str, Any]
    ) -> List[str]:
        """生成执行建议"""
        guidelines = []
        
        # 通用建议
        guidelines.extend([
            "严格遵循周期化计划，不要随意跳过阶段",
            "记录每次训练的重量、组数、次数",
            "根据身体反馈调整训练强度",
            "保证充足睡眠（7-9小时/天）",
            "摄入足够蛋白质（1.6-2.2g/kg体重）"
        ])
        
        # 模型特定建议
        if periodization_model == PeriodizationModel.LINEAR:
            guidelines.extend([
                "线性周期化：逐步增加强度，降低容量",
                "不要急于增加重量，确保动作质量",
                "适应期非常重要，不要跳过"
            ])
        
        elif periodization_model == PeriodizationModel.DUP:
            guidelines.extend([
                "每日波动：严格区分不同强度日",
                "肥大日注重肌肉泵感",
                "力量日注重爆发力和速度",
                "不要在同一天混合不同强度"
            ])
        
        elif periodization_model == PeriodizationModel.BLOCK:
            guidelines.extend([
                "块状周期化：每个块有明确目标",
                "积累块：不要追求大重量",
                "强化块：充分休息，保证质量",
                "实现块：准备测试最大力量"
            ])
        
        elif periodization_model == PeriodizationModel.CONJUGATE:
            guidelines.extend([
                "共轭周期化：频繁变换动作变式",
                "最大力量日：全力以赴",
                "动态力量日：注重速度和爆发力",
                "每周轮换主要动作，防止适应"
            ])
        
        return guidelines
    
    def _generate_important_notes(
        self,
        periodization_model: PeriodizationModel,
        input_data: Dict[str, Any]
    ) -> List[str]:
        """生成注意事项"""
        notes = []
        
        # 通用注意事项
        notes.extend([
            "⚠️ 周期化训练需要长期坚持，不要期待短期效果",
            "⚠️ 如有不适立即停止训练，必要时咨询医生",
            "⚠️ 减量周非常重要，不要跳过",
            "⚠️ 营养和睡眠与训练同等重要"
        ])
        
        # 水平特定注意事项
        difficulty_level = input_data["difficulty_level"]
        
        if difficulty_level == "beginner":
            notes.extend([
                "新手：前2-4周专注于学习动作",
                "不要急于增加重量",
                "建议在教练指导下进行"
            ])
        
        elif difficulty_level == "advanced":
            notes.extend([
                "高级训练者：注意过度训练风险",
                "定期评估恢复状态",
                "考虑使用HRV等工具监测"
            ])
        
        # 损伤史注意事项
        if input_data.get("injury_history"):
            notes.append("⚠️ 有损伤史：避免高风险动作，必要时咨询医疗专业人士")
        
        return notes
    
    def _generate_program_name(
        self,
        periodization_model: PeriodizationModel,
        input_data: Dict[str, Any]
    ) -> str:
        """生成计划名称"""
        model_names = {
            PeriodizationModel.LINEAR: "线性周期化",
            PeriodizationModel.DUP: "每日波动",
            PeriodizationModel.BLOCK: "块状周期化",
            PeriodizationModel.CONJUGATE: "共轭周期化"
        }
        
        goal_names = {
            TrainingGoal.STRENGTH: "力量",
            TrainingGoal.HYPERTROPHY: "肌肥大",
            TrainingGoal.POWER: "爆发力",
            TrainingGoal.ENDURANCE: "耐力",
            TrainingGoal.GENERAL_FITNESS: "综合体能"
        }
        
        model_name = model_names.get(periodization_model, "周期化")
        goal_name = goal_names.get(input_data["training_goal"], "训练")
        weeks = input_data["program_duration_weeks"]
        
        return f"{weeks}周{model_name}{goal_name}计划"
