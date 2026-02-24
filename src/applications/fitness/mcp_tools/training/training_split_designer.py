"""
训练分化设计器 MCP工具

基于用户档案和训练数据，设计个性化的训练分化计划
支持多种分化模式：全身、上下肢、推拉腿、部位分化等

功能特性：
- 根据训练水平、目标和可用时间设计分化方案
- 生成详细的周训练日程表
- 计算训练负荷和恢复建议
- 提供进度跟踪和安全建议

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-15
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
import logging

from ..base_tool import BaseMCPTool
from src.utils.neo4j_result_handler import Neo4jResultHandler

logger = logging.getLogger(__name__)


# =============================================================================
# 枚举类型定义（从权威来源导入）
# =============================================================================

from ...types.enums import TrainingGoal, DifficultyLevel

# 向后兼容别名
TrainingLevel = DifficultyLevel


class SplitType(str, Enum):
    """分化类型"""
    UPPER_LOWER = "upper_lower"
    PUSH_PULL_LEGS = "push_pull_legs"
    BRO_SPLIT = "bro_split"
    FULL_BODY = "full_body"
    THREE_DAY = "three_day"
    FOUR_DAY = "four_day"
    CUSTOM = "custom"
    # 中国本地化新增分化类型
    CHEST_BACK = "chest_back"           # 胸背分化
    ANTAGONIST = "antagonist"           # 拮抗肌分化
    ARNOLD_SPLIT = "arnold_split"       # 阿诺德分化


class RestDayPreference(str, Enum):
    """休息日偏好"""
    CONSECUTIVE = "consecutive"
    SPREAD_OUT = "spread_out"


class RestPattern(str, Enum):
    """
    休息模式枚举（中国本地化）
    
    定义不同的训练与休息天数比例安排，适配中国用户习惯
    Requirements: 2.1, 2.2, 2.3
    """
    # 基础模式
    TRAIN_5_REST_2 = "train_5_rest_2"       # 练五休二（周末休息）- Requirements 2.1
    TRAIN_4_REST_1 = "train_4_rest_1"       # 练四休一 - Requirements 2.2
    TRAIN_3_REST_1 = "train_3_rest_1"       # 练三休一 - Requirements 2.3
    TRAIN_6_REST_1 = "train_6_rest_1"       # 练六休一
    TRAIN_2_REST_1 = "train_2_rest_1"       # 练二休一
    TRAIN_1_REST_1 = "train_1_rest_1"       # 练一休一（隔日训练）
    
    # 大学生推荐模式 - Requirements 2.4
    MON_WED_FRI = "mon_wed_fri"             # 星期一三五
    TUE_THU_SAT = "tue_thu_sat"             # 星期二四六
    
    # 自定义
    CUSTOM = "custom"                        # 自定义模式


class UserType(str, Enum):
    """用户类型（中国本地化）"""
    STUDENT = "student"         # 大学生
    WORKER = "worker"           # 上班族
    OTHER = "other"             # 其他


# =============================================================================
# 输入Schema定义
# =============================================================================

class TrainingSplitDesignerInput(BaseModel):
    """训练分化设计器输入Schema"""
    
    # 用户信息
    user_id: str = Field(..., description="用户ID")
    
    # 训练参数
    training_level: TrainingLevel = Field(..., description="训练水平")
    primary_goal: TrainingGoal = Field(..., description="主要训练目标")
    training_days_per_week: int = Field(..., ge=2, le=6, description="每星期训练天数")
    session_duration_minutes: int = Field(..., ge=30, le=120, description="每次训练时长（分钟）")
    
    # 器械和限制
    available_equipment: List[str] = Field(..., description="可用器械列表")
    muscle_group_focus: Optional[List[str]] = Field(None, description="重点关注肌群（可选）")
    injury_history: Optional[List[str]] = Field(None, description="损伤史（可选）")
    
    # 偏好设置
    preferred_split_type: Optional[SplitType] = Field(None, description="偏好的分化类型（可选）")
    include_cardio: bool = Field(True, description="是否包含有氧训练")
    rest_day_preference: RestDayPreference = Field(RestDayPreference.SPREAD_OUT, description="休息日偏好")
    time_constraints: Optional[str] = Field(None, description="时间限制说明（可选）")
    
    # 中国本地化字段
    user_type: Optional[UserType] = Field(None, description="用户类型（大学生/上班族/其他）")
    preferred_rest_pattern: Optional[RestPattern] = Field(None, description="偏好的休息模式（如练五休二、练四休一等）")


# =============================================================================
# 输出Schema定义
# =============================================================================

class ExerciseInSession(BaseModel):
    """训练日中的动作"""
    exercise_id: str
    name_zh: str
    name_en: str
    primary_muscle: str
    secondary_muscles: List[str]
    equipment_required: List[str]
    difficulty_level: str
    movement_pattern: str
    sets: int
    reps_range: str
    rest_seconds: int


class SessionPlan(BaseModel):
    """训练日计划"""
    session_number: int
    session_name: str
    target_muscle_groups: List[str]
    estimated_duration: int
    exercise_count: int
    exercises: List[ExerciseInSession]
    warm_up_plan: List[str]
    cool_down_plan: List[str]
    intensity_focus: str


class DaySchedule(BaseModel):
    """日程安排"""
    day: str
    is_training_day: bool
    session: Optional[SessionPlan] = None
    estimated_duration: Optional[int] = None
    intensity_level: Optional[str] = None
    activity_type: Optional[str] = None
    recommendations: Optional[List[str]] = None


class LoadRecommendations(BaseModel):
    """训练负荷建议"""
    weekly_volume_guidelines: Dict[str, Any]
    progression_strategy: str
    deload_schedule: str
    rpe_targets: Dict[str, str]
    rest_between_sets: Dict[str, str]
    recovery_metrics: Dict[str, str]


class ProgressTracking(BaseModel):
    """进度跟踪计划"""
    weekly_measurements: List[str]
    biweekly_assessments: List[str]
    monthly_evaluations: List[str]
    key_indicators: List[str]


class SafetyConsideration(BaseModel):
    """安全考虑"""
    category: str
    items: List[str]


class CustomizationNotes(BaseModel):
    """定制化说明"""
    equipment_adaptations: List[str]
    time_saving_tips: List[str]
    progression_modifications: List[str]
    goal_specific_notes: List[str]


class SplitPlan(BaseModel):
    """分化计划"""
    split_type: str
    split_name: str
    description: str
    training_days: int
    session_plans: List[SessionPlan]
    muscle_group_distribution: Dict[str, int]
    estimated_weekly_volume: Dict[str, Any]


class TrainingSplitDesignerOutput(BaseModel):
    """训练分化设计器输出Schema"""
    
    success: bool
    tool_name: str
    user_id: str
    
    # 分化计划
    split_plan: SplitPlan
    
    # 周日程表
    weekly_schedule: List[DaySchedule]
    
    # 负荷建议
    load_recommendations: LoadRecommendations
    
    # 进度跟踪
    progress_tracking: ProgressTracking
    
    # 安全考虑
    safety_considerations: List[SafetyConsideration]
    
    # 定制化说明
    customization_notes: CustomizationNotes
    
    # 元数据
    execution_time_ms: float
    plan_duration_weeks: int


# =============================================================================
# 训练分化设计器类
# =============================================================================

class TrainingSplitDesigner(BaseMCPTool):
    """
    训练分化设计器
    
    根据用户训练水平、目标和可用时间，设计个性化的训练分化计划
    """
    
    def __init__(
        self,
        neo4j_client,
        qdrant_client,
        three_layer_engine,
        logger: Optional[logging.Logger] = None
    ):
        """
        初始化训练分化设计器
        
        Args:
            neo4j_client: Neo4j客户端实例
            qdrant_client: Qdrant客户端实例
            three_layer_engine: 三层检索引擎实例
            logger: 日志记录器（可选）
        """
        super().__init__(neo4j_client, qdrant_client, three_layer_engine, logger)
    
    def get_name(self) -> str:
        return "training_split_designer"
    
    def get_description(self) -> str:
        return "训练分化设计器 - 根据用户训练水平、目标和可用时间，设计个性化的训练分化计划"
    
    def get_category(self) -> str:
        return "training"
    
    def get_input_schema(self) -> type[BaseModel]:
        return TrainingSplitDesignerInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return TrainingSplitDesignerOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 2000.0  # 2秒
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["neo4j", "qdrant", "three_layer_engine"]
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行训练分化设计
        
        流程：
        1. 计算训练周期
        2. 生成分化选项
        3. 选择最优分化方案
        4. 规划训练日
        5. 生成周日程表
        6. 计算负荷建议
        7. 生成进度跟踪和安全建议
        """
        import time
        start_time = time.time()
        
        try:
            # Step 1: 计算训练周期
            cycle_info = self._calculate_training_cycle(input_data)
            
            # Step 2: 生成分化选项
            split_options = self._generate_split_options(input_data)
            
            # Step 3: 选择最优分化方案
            recommended_split = self._select_optimal_split(
                split_options,
                input_data
            )
            
            # Step 4: 规划训练日（基于分化中的训练日，不是日历周）
            session_plans = await self._plan_training_sessions(
                recommended_split,
                input_data
            )
            
            # Step 5: 计算肌群分布和周训练量
            muscle_distribution = self._calculate_muscle_distribution(session_plans)
            weekly_volume = self._calculate_weekly_volume(session_plans)
            
            # 构建分化计划（包含周期信息）
            split_plan = {
                "split_type": recommended_split["type"],
                "split_name": recommended_split["name"],
                "description": recommended_split["description"],
                "training_days": input_data["training_days_per_week"],
                "session_plans": session_plans,
                "muscle_group_distribution": muscle_distribution,
                "estimated_weekly_volume": weekly_volume,
                # 新增周期信息
                "cycle_days": cycle_info["cycle_days"],
                "cycles_per_week": cycle_info["cycles_per_week"],
                "training_pattern": cycle_info["training_pattern"],
                "split_sessions": recommended_split.get("split_sessions", len(session_plans))
            }
            
            # Step 6: 生成周日程表（基于训练周期，不是固定7天）
            weekly_schedule = self._generate_weekly_schedule(
                split_plan,
                input_data,
                cycle_info
            )
            
            # Step 7: 计算负荷建议
            load_recommendations = self._calculate_load_recommendations(
                input_data
            )
            
            # Step 8: 生成进度跟踪计划
            progress_tracking = self._generate_progress_tracking_plan()
            
            # Step 9: 生成安全考虑
            safety_considerations = self._generate_safety_considerations(
                input_data
            )
            
            # Step 10: 生成定制化说明
            customization_notes = self._generate_customization_notes(
                input_data
            )
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": self.get_name(),
                "user_id": input_data["user_id"],
                "split_plan": split_plan,
                "weekly_schedule": weekly_schedule,
                "load_recommendations": load_recommendations,
                "progress_tracking": progress_tracking,
                "safety_considerations": safety_considerations,
                "customization_notes": customization_notes,
                "execution_time_ms": execution_time_ms,
                "plan_duration_weeks": 4,
                # 新增周期信息到顶层
                "cycle_info": cycle_info
            }
            
            self.logger.info(
                f"✅ 训练分化设计完成: {split_plan['split_name']}, "
                f"{input_data['training_days_per_week']}天/周, "
                f"周期={cycle_info['cycle_days']}天, "
                f"模式={cycle_info['training_pattern']}"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"❌ 训练分化设计失败: {e}", exc_info=True)
            raise
    
    def _calculate_training_cycle(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        计算实际训练周期
        
        根据训练分化类型和休息模式计算实际的训练周期：
        - 练五休二（周末休息）= 7天周期
        - 练四休一 = 5天周期
        - 练三休一 = 4天周期
        - 练六休一 = 7天周期
        - 练二休一 = 3天周期
        - 练一休一（隔日训练）= 2天周期
        
        注意：训练周期(cycle)和日历周(week)是不同的概念！
        - 训练周期：完成一轮训练分化所需的天数
        - 日历周：固定7天
        
        Returns:
            Dict包含：
            - cycle_days: 实际周期天数
            - cycles_per_week: 每星期完整周期数
            - training_pattern: 训练模式描述
            - split_sessions: 分化中的训练日数量
            - rest_pattern: 休息模式
        """
        training_days_per_week = input_data["training_days_per_week"]
        rest_day_preference = input_data.get("rest_day_preference", "spread_out")
        preferred_split = input_data.get("preferred_split_type")
        preferred_rest_pattern = input_data.get("preferred_rest_pattern")
        user_type = input_data.get("user_type")
        
        # 如果用户指定了休息模式，优先使用
        if preferred_rest_pattern:
            return self._calculate_cycle_from_rest_pattern(
                preferred_rest_pattern, 
                training_days_per_week,
                preferred_split
            )
        
        # 大学生用户推荐隔日训练 - Requirements 2.4
        if user_type == "student" and training_days_per_week <= 3:
            self.logger.info("🎓 大学生用户，推荐隔日训练模式（星期一三五或星期二四六）")
            return {
                "cycle_days": 7,
                "cycles_per_week": 1.0,
                "training_pattern": "隔日训练（星期一三五）",
                "split_sessions": training_days_per_week,
                "rest_pattern": "mon_wed_fri",
                "recommended_for_student": True
            }
        
        # 根据训练天数和偏好确定分化类型
        if preferred_split == "push_pull_legs" or (training_days_per_week >= 3 and not preferred_split):
            # 推拉腿分化：3个训练日为一个周期
            split_sessions = 3
            
            if training_days_per_week == 3:
                # 练三休一：3训练 + 1休息 = 4天周期
                cycle_days = 4
                training_pattern = "练三休一"
                rest_pattern = "train_3_rest_1"
            elif training_days_per_week == 6:
                # 练六休一：连续两个周期 + 1休息 = 7天周期
                cycle_days = 7
                training_pattern = "练六休一"
                rest_pattern = "train_6_rest_1"
            else:
                # 其他情况：按7天计算
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"
                rest_pattern = "custom"
        
        elif preferred_split == "chest_back":
            # 胸背分化：3个训练日为一个周期（胸背、肩臂、腿）
            split_sessions = 3
            
            if training_days_per_week == 3:
                cycle_days = 4
                training_pattern = "练三休一"
                rest_pattern = "train_3_rest_1"
            elif training_days_per_week == 6:
                cycle_days = 7
                training_pattern = "练六休一"
                rest_pattern = "train_6_rest_1"
            else:
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"
                rest_pattern = "custom"
        
        elif preferred_split == "antagonist":
            # 拮抗肌分化：4个训练日为一个周期
            split_sessions = 4
            
            if training_days_per_week == 4:
                cycle_days = 5
                training_pattern = "练四休一"
                rest_pattern = "train_4_rest_1"
            else:
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"
                rest_pattern = "custom"
        
        elif preferred_split == "arnold_split":
            # 阿诺德分化：6个训练日为一个周期
            split_sessions = 6
            cycle_days = 7
            training_pattern = "练六休一"
            rest_pattern = "train_6_rest_1"
        
        elif preferred_split == "upper_lower" or training_days_per_week == 4:
            # 上下肢分化：2个训练日为一个周期
            split_sessions = 2
            
            if training_days_per_week == 4:
                # 练二休一：2训练 + 1休息 = 3天周期，一周两个周期
                cycle_days = 3
                training_pattern = "练二休一"
                rest_pattern = "train_2_rest_1"
            else:
                # 其他情况：按7天计算
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"
                rest_pattern = "custom"
        
        elif preferred_split == "full_body" or training_days_per_week <= 3:
            # 全身训练：每次训练都是完整周期
            split_sessions = 1
            
            if training_days_per_week == 3:
                # 练一休一：1训练 + 1休息 = 2天周期
                cycle_days = 2
                training_pattern = "练一休一"
                rest_pattern = "train_1_rest_1"
            else:
                # 其他情况：按7天计算
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"
                rest_pattern = "custom"
        
        elif preferred_split == "bro_split" or training_days_per_week >= 5:
            # 部位分化：5-7个训练日为一个周期
            split_sessions = min(training_days_per_week, 6)
            
            if training_days_per_week == 5:
                # 练五休二（周末休息）- Requirements 2.1
                cycle_days = 7
                training_pattern = "练五休二（周末休息）"
                rest_pattern = "train_5_rest_2"
            else:
                cycle_days = 7
                training_pattern = f"每星期{training_days_per_week}天"
                rest_pattern = "custom"
        
        else:
            # 默认：按7天计算
            split_sessions = training_days_per_week
            cycle_days = 7
            training_pattern = f"每星期{training_days_per_week}天"
            rest_pattern = "custom"
        
        # 计算每星期完整周期数
        cycles_per_week = round(7.0 / cycle_days, 2)
        
        self.logger.info(
            f"📊 训练周期计算: "
            f"周期={cycle_days}天, "
            f"每星期{cycles_per_week}个周期, "
            f"模式={training_pattern}, "
            f"分化训练日={split_sessions}, "
            f"休息模式={rest_pattern}"
        )
        
        return {
            "cycle_days": cycle_days,
            "cycles_per_week": cycles_per_week,
            "training_pattern": training_pattern,
            "split_sessions": split_sessions,
            "rest_pattern": rest_pattern
        }
    
    def _calculate_cycle_from_rest_pattern(
        self,
        rest_pattern: str,
        training_days_per_week: int,
        preferred_split: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        根据休息模式计算训练周期
        
        Args:
            rest_pattern: 休息模式
            training_days_per_week: 每星期训练天数
            preferred_split: 偏好的分化类型
            
        Returns:
            训练周期信息
        """
        # 休息模式到周期的映射
        pattern_config = {
            "train_5_rest_2": {
                "cycle_days": 7,
                "training_pattern": "练五休二（周末休息）",
                "split_sessions": 5,
                "description": "星期一至星期五训练，周末休息"
            },
            "train_4_rest_1": {
                "cycle_days": 5,
                "training_pattern": "练四休一",
                "split_sessions": 4,
                "description": "连续训练4天，休息1天"
            },
            "train_3_rest_1": {
                "cycle_days": 4,
                "training_pattern": "练三休一",
                "split_sessions": 3,
                "description": "连续训练3天，休息1天"
            },
            "train_6_rest_1": {
                "cycle_days": 7,
                "training_pattern": "练六休一",
                "split_sessions": 6,
                "description": "连续训练6天，休息1天"
            },
            "train_2_rest_1": {
                "cycle_days": 3,
                "training_pattern": "练二休一",
                "split_sessions": 2,
                "description": "连续训练2天，休息1天"
            },
            "train_1_rest_1": {
                "cycle_days": 2,
                "training_pattern": "练一休一（隔日训练）",
                "split_sessions": 1,
                "description": "训练1天，休息1天"
            },
            "mon_wed_fri": {
                "cycle_days": 7,
                "training_pattern": "星期一三五",
                "split_sessions": 3,
                "description": "星期一、星期三、星期五训练"
            },
            "tue_thu_sat": {
                "cycle_days": 7,
                "training_pattern": "星期二四六",
                "split_sessions": 3,
                "description": "星期二、星期四、星期六训练"
            }
        }
        
        config = pattern_config.get(rest_pattern, {
            "cycle_days": 7,
            "training_pattern": f"每星期{training_days_per_week}天",
            "split_sessions": training_days_per_week,
            "description": "自定义休息模式"
        })
        
        cycle_days = config["cycle_days"]
        cycles_per_week = round(7.0 / cycle_days, 2)
        
        self.logger.info(
            f"📊 根据休息模式计算周期: "
            f"模式={rest_pattern}, "
            f"周期={cycle_days}天, "
            f"每星期{cycles_per_week}个周期"
        )
        
        return {
            "cycle_days": cycle_days,
            "cycles_per_week": cycles_per_week,
            "training_pattern": config["training_pattern"],
            "split_sessions": config["split_sessions"],
            "rest_pattern": rest_pattern,
            "description": config["description"]
        }
    
    def _generate_split_options(
        self,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        生成分化选项
        
        注意：这里生成的是训练周期内的训练日安排，不是日历周的安排
        例如：推拉腿分化只有3个训练日（推、拉、腿），配合休息模式形成完整周期
        """
        options = []
        training_days = input_data["training_days_per_week"]
        
        if training_days == 2:
            options.append({
                "type": "full_body",
                "name": "全身训练分化",
                "description": "每次训练覆盖全身主要肌群，适合初学者和时间紧张的用户",
                "sessions": ["全身训练A", "全身训练B"],
                "muscle_groups": [
                    ["胸大肌", "背阔肌", "股四头肌", "三角肌", "肱二头肌"],
                    ["胸大肌", "背阔肌", "腘绳肌", "三角肌", "肱三头肌"]
                ],
                "split_sessions": 2,  # 分化中的训练日数量
                "recommended_cycle_days": 7,  # 推荐周期天数
                "recommended_pattern": "每星期2天"
            })
        
        elif training_days == 3:
            # 推拉腿分化（3天训练 + 1天休息 = 4天周期）
            options.append({
                "type": "push_pull_legs",
                "name": "推拉腿分化",
                "description": "推拉腿三分化，练三休一，4天为一个训练周期",
                "sessions": ["推日（胸肩三头）", "拉日（背二头）", "腿日"],
                "muscle_groups": [
                    ["胸大肌", "三角肌", "肱三头肌"],
                    ["背阔肌", "肱二头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"]
                ],
                "split_sessions": 3,
                "recommended_cycle_days": 4,
                "recommended_pattern": "练三休一"
            })
            # 胸背分化（中国健身房流行）
            options.append({
                "type": "chest_back",
                "name": "胸背分化",
                "description": "胸+背、肩+臂、腿的三日分化，中国健身房常见方案",
                "sessions": ["胸背日", "肩臂日", "腿日"],
                "muscle_groups": [
                    ["胸大肌", "背阔肌"],
                    ["三角肌", "肱二头肌", "肱三头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"]
                ],
                "split_sessions": 3,
                "recommended_cycle_days": 4,
                "recommended_pattern": "练三休一"
            })
            # 全身训练备选
            options.append({
                "type": "full_body",
                "name": "全身训练分化",
                "description": "每星期3次全身训练，平衡发展各肌群",
                "sessions": ["全身训练A", "全身训练B", "全身训练C"],
                "muscle_groups": [
                    ["胸大肌", "背阔肌", "股四头肌"],
                    ["三角肌", "肱二头肌", "肱三头肌", "腘绳肌"],
                    ["胸大肌", "背阔肌", "臀大肌"]
                ],
                "split_sessions": 3,
                "recommended_cycle_days": 7,
                "recommended_pattern": "每星期3天"
            })
        
        elif training_days == 4:
            # 上下肢分化（2天训练 + 1天休息 = 3天周期）
            options.append({
                "type": "upper_lower",
                "name": "上下肢分化",
                "description": "上下肢交替训练，练二休一，3天为一个训练周期",
                "sessions": ["上肢训练", "下肢训练"],
                "muscle_groups": [
                    ["胸大肌", "背阔肌", "三角肌", "肱二头肌", "肱三头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"]
                ],
                "split_sessions": 2,
                "recommended_cycle_days": 3,
                "recommended_pattern": "练二休一"
            })
            # 拮抗肌分化（将拮抗肌群配对训练）
            options.append({
                "type": "antagonist",
                "name": "拮抗肌分化",
                "description": "将拮抗肌群配对训练，如胸+背、二头+三头，提高训练效率",
                "sessions": ["胸背日", "肩臂日", "腿日A", "腿日B"],
                "muscle_groups": [
                    ["胸大肌", "背阔肌"],
                    ["三角肌", "肱二头肌", "肱三头肌"],
                    ["股四头肌", "臀大肌"],
                    ["腘绳肌", "小腿"]
                ],
                "split_sessions": 4,
                "recommended_cycle_days": 5,
                "recommended_pattern": "练四休一"
            })
        
        elif training_days == 5:
            # 推拉腿分化（高频版本）
            options.append({
                "type": "push_pull_legs",
                "name": "推拉腿分化（高频）",
                "description": "推拉腿三分化，每星期5天训练，适合中高级训练者",
                "sessions": ["推日（胸肩三头）", "拉日（背二头）", "腿日"],
                "muscle_groups": [
                    ["胸大肌", "三角肌", "肱三头肌"],
                    ["背阔肌", "肱二头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"]
                ],
                "split_sessions": 3,
                "recommended_cycle_days": 4,  # 仍然是4天周期，但一周内会完成更多周期
                "recommended_pattern": "练三休一（高频）"
            })
        
        elif training_days == 6:
            # 推拉腿分化（练六休一）
            options.append({
                "type": "push_pull_legs",
                "name": "推拉腿分化（双周期）",
                "description": "推拉腿三分化，练六休一，7天为一个完整周期（包含2轮推拉腿）",
                "sessions": ["推日（胸肩三头）", "拉日（背二头）", "腿日"],
                "muscle_groups": [
                    ["胸大肌", "三角肌", "肱三头肌"],
                    ["背阔肌", "肱二头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"]
                ],
                "split_sessions": 3,
                "recommended_cycle_days": 7,
                "recommended_pattern": "练六休一"
            })
            # 阿诺德分化（胸背、肩臂、腿的六日高频训练）
            options.append({
                "type": "arnold_split",
                "name": "阿诺德分化",
                "description": "经典阿诺德分化，胸背、肩臂、腿各训练两次，适合高级训练者",
                "sessions": ["胸背日A", "肩臂日A", "腿日A", "胸背日B", "肩臂日B", "腿日B"],
                "muscle_groups": [
                    ["胸大肌", "背阔肌"],
                    ["三角肌", "肱二头肌", "肱三头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"],
                    ["胸大肌", "背阔肌"],
                    ["三角肌", "肱二头肌", "肱三头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"]
                ],
                "split_sessions": 6,
                "recommended_cycle_days": 7,
                "recommended_pattern": "练六休一"
            })
            # 部位分化备选
            options.append({
                "type": "bro_split",
                "name": "部位分化",
                "description": "经典的部位分化，高训练量，适合高级训练者",
                "sessions": ["胸部", "背部", "肩部", "手臂", "腿部", "核心"],
                "muscle_groups": [
                    ["胸大肌"],
                    ["背阔肌"],
                    ["三角肌"],
                    ["肱二头肌", "肱三头肌"],
                    ["股四头肌", "腘绳肌", "臀大肌"],
                    ["腹直肌", "腹外斜肌"]
                ],
                "split_sessions": 6,
                "recommended_cycle_days": 7,
                "recommended_pattern": "每星期6天"
            })
        
        return options
    
    def _select_optimal_split(
        self,
        options: List[Dict[str, Any]],
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        选择最优分化方案
        
        推荐逻辑：
        1. 用户有偏好 → 优先选择用户偏好
        2. 大学生用户且时间有限 → 推荐全身训练或上下肢分化
        3. 初学者 → 推荐全身训练
        4. 力量目标 → 推荐全身或上下肢分化
        5. 默认 → 返回第一个选项
        """
        # 如果用户有偏好，优先选择
        if input_data.get("preferred_split_type"):
            preferred = next(
                (opt for opt in options if opt["type"] == input_data["preferred_split_type"]),
                None
            )
            if preferred:
                return preferred
        
        # 大学生用户推荐逻辑（Requirements 1.4）
        user_type = input_data.get("user_type")
        training_days = input_data.get("training_days_per_week", 3)
        
        if user_type == "student":
            # 大学生时间有限，推荐全身训练或上下肢分化
            if training_days <= 3:
                # 每星期3天或更少，推荐全身训练
                full_body = next((opt for opt in options if opt["type"] == "full_body"), None)
                if full_body:
                    self.logger.info("🎓 大学生用户，推荐全身训练分化（时间效率高）")
                    return full_body
            elif training_days == 4:
                # 每星期4天，推荐上下肢分化
                upper_lower = next((opt for opt in options if opt["type"] == "upper_lower"), None)
                if upper_lower:
                    self.logger.info("🎓 大学生用户，推荐上下肢分化（平衡效率与效果）")
                    return upper_lower
        
        # 根据训练水平选择
        if input_data["training_level"] == "beginner":
            full_body = next((opt for opt in options if opt["type"] == "full_body"), None)
            if full_body:
                return full_body
        
        # 根据目标调整
        if input_data["primary_goal"] == "strength":
            for opt in options:
                if opt["type"] in ["full_body", "upper_lower"]:
                    return opt
        
        # 默认返回第一个选项
        return options[0] if options else {
            "type": "full_body",
            "name": "全身训练",
            "description": "默认全身训练方案",
            "sessions": ["全身训练"],
            "muscle_groups": [["胸大肌", "背阔肌", "股四头肌"]],
            "split_sessions": 1,
            "recommended_cycle_days": 7,
            "recommended_pattern": "每星期训练"
        }
    
    def recommend_rest_pattern(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        根据用户类型和分化类型智能推荐休息模式
        
        推荐逻辑 - Requirements 2.4, 2.5：
        1. 大学生用户 → 推荐隔日训练（星期一三五或星期二四六）
        2. 上班族用户 → 推荐练五休二（周末休息）
        3. 根据分化类型智能推荐：
           - 推拉腿/胸背分化 → 练三休一或练六休一
           - 拮抗肌分化 → 练四休一
           - 上下肢分化 → 练二休一
           - 全身训练 → 练一休一（隔日训练）
        
        Args:
            input_data: 输入数据
            
        Returns:
            推荐的休息模式信息
        """
        user_type = input_data.get("user_type")
        training_days = input_data.get("training_days_per_week", 3)
        preferred_split = input_data.get("preferred_split_type")
        
        # 大学生推荐隔日训练 - Requirements 2.4
        if user_type == "student":
            if training_days <= 3:
                self.logger.info("🎓 大学生用户，推荐隔日训练模式")
                return {
                    "recommended_pattern": "mon_wed_fri",
                    "pattern_name": "星期一三五",
                    "description": "适合大学生课程安排，隔日训练有利于恢复",
                    "alternative": "tue_thu_sat",
                    "alternative_name": "星期二四六",
                    "reason": "大学生时间有限，隔日训练既能保证训练效果，又能兼顾学业"
                }
        
        # 上班族推荐练五休二 - Requirements 2.1
        if user_type == "worker":
            if training_days == 5:
                self.logger.info("💼 上班族用户，推荐练五休二模式")
                return {
                    "recommended_pattern": "train_5_rest_2",
                    "pattern_name": "练五休二（周末休息）",
                    "description": "星期一至星期五训练，周末休息，适合上班族作息",
                    "reason": "与工作日程同步，周末可以充分休息和恢复"
                }
        
        # 根据分化类型智能推荐 - Requirements 2.5
        split_pattern_map = {
            "push_pull_legs": {
                3: {"pattern": "train_3_rest_1", "name": "练三休一"},
                6: {"pattern": "train_6_rest_1", "name": "练六休一"}
            },
            "chest_back": {
                3: {"pattern": "train_3_rest_1", "name": "练三休一"},
                6: {"pattern": "train_6_rest_1", "name": "练六休一"}
            },
            "antagonist": {
                4: {"pattern": "train_4_rest_1", "name": "练四休一"}
            },
            "arnold_split": {
                6: {"pattern": "train_6_rest_1", "name": "练六休一"}
            },
            "upper_lower": {
                4: {"pattern": "train_2_rest_1", "name": "练二休一"}
            },
            "full_body": {
                3: {"pattern": "train_1_rest_1", "name": "练一休一（隔日训练）"}
            },
            "bro_split": {
                5: {"pattern": "train_5_rest_2", "name": "练五休二（周末休息）"},
                6: {"pattern": "train_6_rest_1", "name": "练六休一"}
            }
        }
        
        if preferred_split and preferred_split in split_pattern_map:
            split_patterns = split_pattern_map[preferred_split]
            if training_days in split_patterns:
                pattern_info = split_patterns[training_days]
                self.logger.info(f"📊 根据分化类型推荐休息模式: {pattern_info['name']}")
                return {
                    "recommended_pattern": pattern_info["pattern"],
                    "pattern_name": pattern_info["name"],
                    "description": f"根据{preferred_split}分化类型和每星期{training_days}天训练推荐",
                    "reason": f"该休息模式与{preferred_split}分化类型最为匹配"
                }
        
        # 默认推荐
        default_patterns = {
            2: {"pattern": "train_2_rest_1", "name": "练二休一"},
            3: {"pattern": "train_3_rest_1", "name": "练三休一"},
            4: {"pattern": "train_4_rest_1", "name": "练四休一"},
            5: {"pattern": "train_5_rest_2", "name": "练五休二（周末休息）"},
            6: {"pattern": "train_6_rest_1", "name": "练六休一"}
        }
        
        if training_days in default_patterns:
            pattern_info = default_patterns[training_days]
            return {
                "recommended_pattern": pattern_info["pattern"],
                "pattern_name": pattern_info["name"],
                "description": f"根据每星期{training_days}天训练推荐",
                "reason": "通用推荐，适合大多数用户"
            }
        
        return {
            "recommended_pattern": "custom",
            "pattern_name": f"每星期{training_days}天",
            "description": "自定义休息模式",
            "reason": "根据个人情况灵活安排"
        }
    
    async def _plan_training_sessions(
        self,
        split_plan: Dict[str, Any],
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """规划训练日"""
        session_plans = []
        
        for i, session_name in enumerate(split_plan["sessions"]):
            muscle_groups = split_plan["muscle_groups"][i]
            
            # 为每个训练日选择动作
            exercises = await self._select_exercises_for_session(
                muscle_groups,
                input_data
            )
            
            session_plan = {
                "session_number": i + 1,
                "session_name": session_name,
                "target_muscle_groups": muscle_groups,
                "estimated_duration": input_data["session_duration_minutes"],
                "exercise_count": len(exercises),
                "exercises": exercises,
                "warm_up_plan": self._generate_warm_up_plan(muscle_groups),
                "cool_down_plan": self._generate_cool_down_plan(muscle_groups),
                "intensity_focus": self._determine_intensity_focus(input_data["primary_goal"])
            }
            
            session_plans.append(session_plan)
        
        return session_plans
    
    async def _select_exercises_for_session(
        self,
        muscle_groups: List[str],
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        为训练日选择动作
        
        使用Neo4jResultHandler处理查询结果，解决：
        1. 'list' object has no attribute 'records' 错误
        2. 使用正确的属性名 primary_muscle_zh（单数形式）
        3. 空结果时使用预设默认动作列表
        4. 肌群名称映射（解剖学名称 -> Neo4j标准名称）
        5. difficulty映射（英文枚举 -> 中文）
        
        Args:
            muscle_groups: 目标肌群列表
            input_data: 输入数据
            
        Returns:
            动作列表
        """
        exercises = []
        
        # 肌群名称映射（解剖学名称 -> Neo4j Muscle.name_zh）
        muscle_name_mapping = {
            "胸大肌": "胸部",
            "胸肌": "胸部",
            "背阔肌": "背阔肌",
            "背部": "背阔肌",
            "股四头肌": "股四头肌",
            "大腿前侧": "股四头肌",
            "三角肌": "肩部",
            "肩部": "肩部",
            "肱二头肌": "肱二头肌",
            "二头肌": "肱二头肌",
            "肱三头肌": "肱三头肌",
            "三头肌": "肱三头肌",
            "腘绳肌": "腿后肌群",
            "大腿后侧": "腿后肌群",
            "臀大肌": "臀部",
            "臀部": "臀部",
            "腹直肌": "腹直肌",
            "腹肌": "腹直肌",
            "小腿": "小腿",
            "斜方肌": "斜方肌",
            "前臂": "前臂肌群",
        }
        
        # difficulty映射（英文枚举 -> 中文）
        # 注意：当前Neo4j中所有Exercise.difficulty都是"中级"
        difficulty_mapping = {
            "beginner": "初级",
            "intermediate": "中级",
            "advanced": "高级",
            "novice": "初级",
        }
        
        # 如果没有Neo4j客户端，返回模拟数据
        if not self.neo4j_client:
            return self._get_default_exercises_for_session(muscle_groups, input_data)
        
        # 使用Neo4j查询真实动作
        for muscle_group in muscle_groups:
            # 映射肌群名称（解剖学名称 -> Neo4j标准名称）
            mapped_muscle = muscle_name_mapping.get(muscle_group, muscle_group)
            
            # 映射difficulty（英文枚举 -> 中文）
            # 获取training_level，处理枚举对象
            training_level_raw = str(input_data.get("training_level", "intermediate"))
            # 移除可能的枚举类名前缀
            if "." in training_level_raw:
                training_level_raw = training_level_raw.split(".")[-1].lower()
            mapped_difficulty = difficulty_mapping.get(training_level_raw.lower(), "中级")
            
            # 查询适合该肌群的动作
            # 注意：当前Neo4j中所有Exercise.difficulty都是"中级"，所以暂时移除difficulty过滤
            query = """
            MATCH (e:Exercise)-[:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m:Muscle)
            WHERE m.name_zh = $muscleGroup
            RETURN e {
              .id,
              .name_zh,
              .name_en,
              .category,
              .difficulty_zh,
              .force_zh,
              .mechanic_zh,
              .equipment_zh,
              .primary_muscle_zh,
              .all_muscles_zh
            } as exercise
            ORDER BY rand()
            LIMIT 2
            """
            
            try:
                result = await self.neo4j_client.execute_query(
                    query,
                    {
                        "muscleGroup": mapped_muscle
                    }
                )
                
                # 使用Neo4jResultHandler统一处理结果
                records = Neo4jResultHandler.to_records(result)
                
                if not records:
                    self.logger.warning(f"肌群 {muscle_group} (映射为 {mapped_muscle}) 查询返回空结果，使用默认动作")
                    exercises.extend(self._get_default_exercises_for_muscle_group(
                        muscle_group, input_data
                    ))
                    continue
                
                for record in records:
                    # 安全获取exercise对象
                    ex = Neo4jResultHandler.get_property(record, "exercise", {})
                    if not ex:
                        continue
                    
                    # 根据训练目标设置组数和次数
                    # 处理primary_goal可能为空的情况
                    primary_goal = input_data.get("primary_goal", "hypertrophy")
                    if not primary_goal:
                        primary_goal = "hypertrophy"
                    sets, reps_range, rest_seconds = self._get_training_parameters(primary_goal)
                    
                    # 安全获取所有属性，处理属性不存在的情况
                    # 使用all_muscles_zh获取所有相关肌群，或使用primary_muscle_zh
                    secondary_muscles = Neo4jResultHandler.safe_list(
                        ex.get("all_muscles_zh"),
                        default=[]
                    )
                    
                    # 使用primary_muscle_zh（单数形式，这是数据库中实际存在的属性）
                    primary_muscles = Neo4jResultHandler.safe_list(
                        ex.get("primary_muscle_zh"),
                        default=[muscle_group]
                    )
                    
                    exercise_data = {
                        "exercise_id": ex.get("id", ""),
                        "name_zh": ex.get("name_zh", "未知动作"),
                        "name_en": ex.get("name_en", "Unknown"),
                        "primary_muscle": muscle_group,
                        "primary_muscles": primary_muscles,
                        "secondary_muscles": secondary_muscles,
                        "equipment_required": Neo4jResultHandler.safe_list(
                            ex.get("equipment_zh"),
                            default=[]
                        ),
                        "difficulty_level": ex.get("difficulty_zh") or ex.get("difficulty_en") or input_data["training_level"],
                        "movement_pattern": ex.get("mechanic_zh") or ex.get("mechanic_en") or "复合",
                        "sets": sets,
                        "reps_range": reps_range,
                        "rest_seconds": rest_seconds
                    }
                    
                    exercises.append(exercise_data)
            
            except Exception as e:
                self.logger.error(f"查询动作失败: {e}", exc_info=True)
                # 查询失败时使用默认动作
                exercises.extend(self._get_default_exercises_for_muscle_group(
                    muscle_group, input_data
                ))
                continue
        
        # 如果没有查询到任何动作，使用完整的默认动作列表
        if not exercises:
            self.logger.warning("所有肌群查询均失败，使用完整默认动作列表")
            return self._get_default_exercises_for_session(muscle_groups, input_data)
        
        return exercises[:8]  # 限制每个训练日最多8个动作
    
    def _get_default_exercises_for_session(
        self,
        muscle_groups: List[str],
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        获取训练日的默认动作列表
        
        当Neo4j查询失败或返回空结果时使用
        
        Args:
            muscle_groups: 目标肌群列表
            input_data: 输入数据
            
        Returns:
            默认动作列表
        """
        exercises = []
        for muscle_group in muscle_groups:
            exercises.extend(self._get_default_exercises_for_muscle_group(
                muscle_group, input_data
            ))
        return exercises[:8]
    
    def _get_default_exercises_for_muscle_group(
        self,
        muscle_group: str,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        获取单个肌群的默认动作列表
        
        预设的默认动作，确保即使Neo4j查询失败也能返回合理的训练计划
        
        Args:
            muscle_group: 目标肌群
            input_data: 输入数据
            
        Returns:
            默认动作列表（2个动作）
        """
        sets, reps_range, rest_seconds = self._get_training_parameters(
            input_data["primary_goal"]
        )
        
        # 预设的默认动作映射
        default_exercises_map = {
            "胸大肌": [
                {"id": "default_chest_1", "name_zh": "杠铃卧推", "name_en": "Barbell Bench Press", "pattern": "复合"},
                {"id": "default_chest_2", "name_zh": "哑铃飞鸟", "name_en": "Dumbbell Fly", "pattern": "孤立"}
            ],
            "背阔肌": [
                {"id": "default_back_1", "name_zh": "引体向上", "name_en": "Pull Up", "pattern": "复合"},
                {"id": "default_back_2", "name_zh": "杠铃划船", "name_en": "Barbell Row", "pattern": "复合"}
            ],
            "股四头肌": [
                {"id": "default_quad_1", "name_zh": "杠铃深蹲", "name_en": "Barbell Squat", "pattern": "复合"},
                {"id": "default_quad_2", "name_zh": "腿举", "name_en": "Leg Press", "pattern": "复合"}
            ],
            "腘绳肌": [
                {"id": "default_ham_1", "name_zh": "罗马尼亚硬拉", "name_en": "Romanian Deadlift", "pattern": "复合"},
                {"id": "default_ham_2", "name_zh": "腿弯举", "name_en": "Leg Curl", "pattern": "孤立"}
            ],
            "三角肌": [
                {"id": "default_delt_1", "name_zh": "杠铃推举", "name_en": "Overhead Press", "pattern": "复合"},
                {"id": "default_delt_2", "name_zh": "侧平举", "name_en": "Lateral Raise", "pattern": "孤立"}
            ],
            "肱二头肌": [
                {"id": "default_bicep_1", "name_zh": "杠铃弯举", "name_en": "Barbell Curl", "pattern": "孤立"},
                {"id": "default_bicep_2", "name_zh": "哑铃锤式弯举", "name_en": "Hammer Curl", "pattern": "孤立"}
            ],
            "肱三头肌": [
                {"id": "default_tricep_1", "name_zh": "窄距卧推", "name_en": "Close Grip Bench Press", "pattern": "复合"},
                {"id": "default_tricep_2", "name_zh": "绳索下压", "name_en": "Cable Pushdown", "pattern": "孤立"}
            ],
            "臀大肌": [
                {"id": "default_glute_1", "name_zh": "臀桥", "name_en": "Hip Thrust", "pattern": "孤立"},
                {"id": "default_glute_2", "name_zh": "保加利亚分腿蹲", "name_en": "Bulgarian Split Squat", "pattern": "复合"}
            ],
            "腹直肌": [
                {"id": "default_abs_1", "name_zh": "卷腹", "name_en": "Crunch", "pattern": "孤立"},
                {"id": "default_abs_2", "name_zh": "平板支撑", "name_en": "Plank", "pattern": "孤立"}
            ],
            "腹外斜肌": [
                {"id": "default_oblique_1", "name_zh": "俄罗斯转体", "name_en": "Russian Twist", "pattern": "孤立"},
                {"id": "default_oblique_2", "name_zh": "侧平板支撑", "name_en": "Side Plank", "pattern": "孤立"}
            ]
        }
        
        # 获取该肌群的默认动作，如果没有则使用通用默认
        default_exercises = default_exercises_map.get(muscle_group, [
            {"id": f"default_{muscle_group}_1", "name_zh": f"{muscle_group}训练动作1", "name_en": f"{muscle_group} Exercise 1", "pattern": "复合"},
            {"id": f"default_{muscle_group}_2", "name_zh": f"{muscle_group}训练动作2", "name_en": f"{muscle_group} Exercise 2", "pattern": "孤立"}
        ])
        
        exercises = []
        for ex in default_exercises:
            exercises.append({
                "exercise_id": ex["id"],
                "name_zh": ex["name_zh"],
                "name_en": ex["name_en"],
                "primary_muscle": muscle_group,
                "primary_muscles": [muscle_group],
                "secondary_muscles": [],
                "equipment_required": input_data.get("available_equipment", [])[:1] if input_data.get("available_equipment") else [],
                "difficulty_level": input_data["training_level"],
                "movement_pattern": ex["pattern"],
                "sets": sets,
                "reps_range": reps_range,
                "rest_seconds": rest_seconds
            })
        
        return exercises
    
    def _get_training_parameters(
        self,
        goal: str
    ) -> tuple[int, str, int]:
        """根据训练目标获取训练参数"""
        if goal == "strength":
            return (5, "3-5", 180)  # 5组，3-5次，180秒休息
        elif goal == "hypertrophy":
            return (4, "8-12", 90)  # 4组，8-12次，90秒休息
        elif goal == "endurance":
            return (3, "15-20", 60)  # 3组，15-20次，60秒休息
        elif goal == "power":
            return (5, "1-5", 180)  # 5组，1-5次，180秒休息
        else:  # general_fitness
            return (3, "10-15", 75)  # 3组，10-15次，75秒休息
    
    def _generate_warm_up_plan(self, muscle_groups: List[str]) -> List[str]:
        """生成热身计划"""
        return [
            "5-10分钟有氧运动",
            f"动态拉伸{', '.join(muscle_groups[:2])}",
            "轻重量热身组（2-3组）"
        ]
    
    def _generate_cool_down_plan(self, muscle_groups: List[str]) -> List[str]:
        """生成放松计划"""
        return [
            "5-10分钟轻度有氧",
            f"静态拉伸{', '.join(muscle_groups[:2])}",
            "深呼吸放松"
        ]
    
    def _determine_intensity_focus(self, goal: str) -> str:
        """确定强度重点"""
        focuses = {
            "strength": "最大力量输出",
            "hypertrophy": "肌肉张力控制",
            "endurance": "持续收缩能力",
            "general_fitness": "全面身体素质",
            "power": "爆发力发展"
        }
        return focuses.get(goal, "全面身体素质")
    
    def _calculate_muscle_distribution(
        self,
        session_plans: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        """计算肌群分布"""
        distribution = {}
        
        for session in session_plans:
            for muscle_group in session["target_muscle_groups"]:
                distribution[muscle_group] = distribution.get(muscle_group, 0) + 1
        
        return distribution
    
    def _calculate_weekly_volume(
        self,
        session_plans: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算周训练量"""
        total_exercises = sum(session["exercise_count"] for session in session_plans)
        total_sets = sum(
            sum(ex["sets"] for ex in session["exercises"])
            for session in session_plans
        )
        avg_duration = sum(
            session["estimated_duration"] for session in session_plans
        ) / len(session_plans) if session_plans else 0
        
        return {
            "total_exercises": total_exercises,
            "total_sets": total_sets,
            "average_session_duration": int(avg_duration)
        }
    
    def _generate_weekly_schedule(
        self,
        split_plan: Dict[str, Any],
        input_data: Dict[str, Any],
        cycle_info: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        生成周日程表
        
        注意：这里生成的是基于训练周期的日程，不是固定的7天日历周
        例如：推拉腿+练三休一 = 4天周期（推→拉→腿→休息）
        
        Args:
            split_plan: 分化计划
            input_data: 输入数据
            cycle_info: 训练周期信息
        """
        cycle_days = cycle_info["cycle_days"]
        training_pattern = cycle_info["training_pattern"]
        session_plans = split_plan["session_plans"]
        
        schedule = []
        session_index = 0
        
        # 生成一个完整训练周期的日程
        for day_num in range(1, cycle_days + 1):
            # 判断是训练日还是休息日
            if session_index < len(session_plans):
                # 训练日
                schedule.append({
                    "day": f"第{day_num}天",
                    "day_in_cycle": day_num,
                    "is_training_day": True,
                    "session": session_plans[session_index],
                    "estimated_duration": session_plans[session_index]["estimated_duration"],
                    "intensity_level": self._calculate_daily_intensity(
                        session_index,
                        input_data["primary_goal"]
                    ),
                    "activity_type": "training",
                    "recommendations": None
                })
                session_index += 1
            else:
                # 休息日
                schedule.append({
                    "day": f"第{day_num}天",
                    "day_in_cycle": day_num,
                    "is_training_day": False,
                    "session": None,
                    "estimated_duration": None,
                    "intensity_level": None,
                    "activity_type": "rest_or_active_recovery",
                    "recommendations": self._generate_rest_day_recommendations(
                        input_data["primary_goal"]
                    )
                })
        
        # 添加周期信息到日程表
        cycle_schedule = {
            "cycle_days": cycle_days,
            "training_pattern": training_pattern,
            "cycles_per_week": cycle_info["cycles_per_week"],
            "schedule": schedule,
            "note": f"这是一个{cycle_days}天的训练周期（{training_pattern}），"
                    f"每星期可完成约{cycle_info['cycles_per_week']:.1f}个周期"
        }
        
        return [cycle_schedule]  # 返回周期日程表
    
    def _calculate_daily_intensity(self, session_index: int, goal: str) -> str:
        """计算每日强度"""
        intensities = ["高强度", "中强度", "高强度", "中强度", "高强度"]
        if goal in ["strength", "hypertrophy"]:
            return intensities[session_index % len(intensities)]
        return "中等强度"
    
    def _generate_rest_day_recommendations(self, goal: str) -> List[str]:
        """生成休息日建议"""
        if goal == "hypertrophy":
            return ["轻度有氧运动（20-30分钟）", "拉伸和放松"]
        return ["完全休息", "轻度活动促进血液循环"]
    
    def _calculate_load_recommendations(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """计算负荷建议"""
        return {
            "weekly_volume_guidelines": self._calculate_volume_guidelines(
                input_data["training_level"]
            ),
            "progression_strategy": self._get_progression_strategy(
                input_data["primary_goal"]
            ),
            "deload_schedule": self._get_deload_schedule(
                input_data["training_level"]
            ),
            "rpe_targets": self._get_rpe_targets(
                input_data["primary_goal"],
                input_data["training_level"]
            ),
            "rest_between_sets": self._get_rest_recommendations(
                input_data["primary_goal"]
            ),
            "recovery_metrics": self._get_recovery_metrics()
        }
    
    def _calculate_volume_guidelines(self, level: str) -> Dict[str, Any]:
        """计算训练量指南"""
        guidelines = {
            "beginner": {"sets": 8, "reps": "8-12"},
            "intermediate": {"sets": 12, "reps": "6-12"},
            "advanced": {"sets": 16, "reps": "4-12"}
        }
        return guidelines.get(level, {"sets": 10, "reps": "8-12"})
    
    def _get_progression_strategy(self, goal: str) -> str:
        """获取渐进策略"""
        strategies = {
            "strength": "线性加重：每星期增加2.5-5kg负荷，直到达到重复次数上限",
            "hypertrophy": "双轨渐进：先增加重复次数，再增加负荷",
            "endurance": "密度训练：逐渐增加训练密度和持续时间",
            "general_fitness": "混合渐进：力量和耐力并重，逐步提升",
            "power": "复合训练：结合力量和速度训练"
        }
        return strategies.get(goal, "混合渐进")
    
    def _get_deload_schedule(self, level: str) -> str:
        """获取减载计划"""
        schedules = {
            "beginner": "每4-6周进行一次减载周，减少30%训练量",
            "intermediate": "每6-8周进行一次减载周，减少40%训练量",
            "advanced": "每8-12周进行一次减载周，减少50%训练量"
        }
        return schedules.get(level, "每6周进行一次减载周")
    
    def _get_rpe_targets(self, goal: str, level: str) -> Dict[str, str]:
        """获取RPE目标"""
        return {
            "target_rpe": "7-9" if goal == "strength" else "6-8",
            "rir_targets": "1-3" if goal == "strength" else "2-4",
            "effort_scale": "1-10分制，10分为力竭"
        }
    
    def _get_rest_recommendations(self, goal: str) -> Dict[str, str]:
        """获取休息建议"""
        return {
            "strength_training": "2-4分钟（复合动作）",
            "hypertrophy": "60-90秒（孤立动作）",
            "endurance": "30-60秒",
            "supersets": "无休息或短暂休息"
        }
    
    def _get_recovery_metrics(self) -> Dict[str, str]:
        """获取恢复指标"""
        return {
            "heart_rate_variability": "晨起HRV应保持在基线80%以上",
            "sleep_quality": "每晚7-9小时优质睡眠",
            "muscle_soreness": "训练后24-48小时轻度酸痛为正常",
            "performance_indicators": "力量、重复次数、训练密度的变化趋势"
        }
    
    def _generate_progress_tracking_plan(self) -> Dict[str, Any]:
        """生成进度跟踪计划"""
        return {
            "weekly_measurements": [
                "体重和体脂率",
                "主要动作的1RM测试",
                "训练日志记录"
            ],
            "biweekly_assessments": [
                "身体围度测量",
                "肌肉对称性评估",
                "动作技术评估"
            ],
            "monthly_evaluations": [
                "整体训练计划调整",
                "营养计划优化",
                "长期目标进度检查"
            ],
            "key_indicators": [
                "力量增长",
                "肌肉围度变化",
                "训练持续性",
                "恢复质量"
            ]
        }
    
    def _generate_safety_considerations(
        self,
        input_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """生成安全考虑"""
        considerations = []
        
        if input_data.get("injury_history"):
            considerations.append({
                "category": "损伤预防",
                "items": [
                    "根据损伤史调整训练动作",
                    "增加热身时间和强度",
                    "重点关注薄弱环节的强化"
                ]
            })
        
        considerations.append({
            "category": "技术要点",
            "items": [
                "每个动作都要注重技术质量",
                "逐渐增加负荷，避免急于求成",
                "倾听身体信号，及时调整"
            ]
        })
        
        considerations.append({
            "category": "恢复管理",
            "items": [
                "保证充足睡眠（7-9小时）",
                "合理安排训练和休息时间",
                "适当的有氧运动促进恢复"
            ]
        })
        
        return considerations
    
    def _generate_customization_notes(
        self,
        input_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """生成定制化说明"""
        return {
            "equipment_adaptations": self._generate_equipment_adaptations(
                input_data["available_equipment"]
            ),
            "time_saving_tips": self._generate_time_saving_tips(
                input_data["session_duration_minutes"]
            ),
            "progression_modifications": self._generate_progression_modifications(
                input_data["training_level"]
            ),
            "goal_specific_notes": self._generate_goal_specific_notes(
                input_data["primary_goal"]
            )
        }
    
    def _generate_equipment_adaptations(
        self,
        equipment: List[str]
    ) -> List[str]:
        """生成器械适配建议"""
        adaptations = []
        
        if "杠铃" not in equipment:
            adaptations.append("可以使用哑铃替代杠铃动作")
        
        if "史密斯机" not in equipment:
            adaptations.append("可以使用自由重量替代史密斯机动作")
        
        if not adaptations:
            adaptations.append("器械配置完善，可以执行所有推荐动作")
        
        return adaptations
    
    def _generate_time_saving_tips(self, duration: int) -> List[str]:
        """生成节省时间建议"""
        tips = []
        
        if duration < 60:
            tips.extend([
                "采用超级组训练节省时间",
                "减少组间休息时间",
                "重点训练主要肌群，简化辅助动作"
            ])
        else:
            tips.append("训练时间充足，可以充分执行所有动作")
        
        return tips
    
    def _generate_progression_modifications(self, level: str) -> List[str]:
        """生成渐进修改建议"""
        modifications = []
        
        if level == "beginner":
            modifications.extend([
                "重点学习动作技术，负荷增加要保守",
                "每个动作都要从最基础的变式开始"
            ])
        elif level == "intermediate":
            modifications.append("可以尝试更高级的训练技巧")
        else:  # advanced
            modifications.append("可以使用高级训练方法如渐降组、强迫次数等")
        
        return modifications
    
    def _generate_goal_specific_notes(self, goal: str) -> List[str]:
        """生成目标特定说明"""
        notes = []
        
        if goal == "hypertrophy":
            notes.extend([
                "重点关注肌肉在张力下的时间",
                "每个肌群每星期训练2-3次"
            ])
        elif goal == "strength":
            notes.extend([
                "主要使用复合动作",
                "低重复次数，高负荷训练"
            ])
        elif goal == "endurance":
            notes.extend([
                "高重复次数，短休息时间",
                "注重训练密度"
            ])
        else:
            notes.append("平衡发展各项身体素质")
        
        return notes
