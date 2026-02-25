"""
Python MCP工具模块

提供统一的MCP工具基类、注册表和异常类型

增强功能 (v2.0.0):
- 标准化三层检索调用 - Requirements 17.1-17.6
- 版本管理 - Requirements 12.1-12.5
"""

from .base_tool import (
    BaseMCPTool,
    ToolMetadata,
    VersionInfo,
    ChangelogEntry,
    ThreeLayerQueryResult,
    MCPToolVersionRegistry,
    get_version_registry
)
from .exceptions import (
    ToolError,
    ToolValidationError,
    ToolTimeoutError,
    ToolConnectionError,
    ToolExecutionError
)
from .registry import MCPToolRegistry

# 导入具体工具
from .exercise.intelligent_exercise_selector import IntelligentExerciseSelector
from .exercise.exercise_alternative_finder import ExerciseAlternativeFinder
from .safety.contraindications_checker import ContraindicationsChecker
from .safety.injury_risk_assessor import InjuryRiskAssessor
from .safety.safe_exercise_modifier import SafeExerciseModifier
from .training.muscle_group_volume_calculator import MuscleGroupVolumeCalculator
from .training.movement_pattern_balancer import MovementPatternBalancer
from .training.intelligent_weight_calculator import IntelligentWeightCalculator
from .training.professional_program_designer import ProfessionalProgramDesigner
from .training.periodized_program_designer import PeriodizedProgramDesigner
from .training.training_split_designer import TrainingSplitDesigner
from .training.record_training_feedback import RecordTrainingFeedback
from .nutrition.tdee_calculator import TDEECalculator
from .nutrition.nutrition_intake_analyzer import NutritionIntakeAnalyzer
from .nutrition.meal_plan_designer import MealPlanDesigner
from .nutrition.exercise_nutrition_optimization import ExerciseNutritionOptimization
from .safety.postural_assessor import PosturalAssessor
from .find_similar_training_cases import FindSimilarTrainingCasesTool


def initialize_all_tools(
    registry: MCPToolRegistry,
    neo4j_client=None,
    qdrant_client=None,
    three_layer_engine=None,
    backend_client=None,
    vector_store=None
) -> None:
    """
    初始化并注册所有18个Python MCP工具

    Args:
        registry: MCPToolRegistry实例
        neo4j_client: Neo4j客户端实例
        qdrant_client: Qdrant客户端实例
        three_layer_engine: 三层检索引擎实例
        backend_client: 后端客户端实例（用于find_similar_training_cases）
        vector_store: 向量存储实例（用于find_similar_training_cases）
    """
    # P0核心工具（5个）
    registry.register_tool(IntelligentExerciseSelector(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(ContraindicationsChecker(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(InjuryRiskAssessor(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(MuscleGroupVolumeCalculator(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(TDEECalculator(neo4j_client, qdrant_client, three_layer_engine))
    
    # P1建议工具（9个）
    # 注意：ProfessionalProgramDesigner需要tool_registry来调用其他工具
    registry.register_tool(ProfessionalProgramDesigner(neo4j_client, qdrant_client, three_layer_engine, tool_registry=registry))
    registry.register_tool(ExerciseAlternativeFinder(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(MovementPatternBalancer(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(IntelligentWeightCalculator(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(SafeExerciseModifier(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(NutritionIntakeAnalyzer(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(MealPlanDesigner(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(ExerciseNutritionOptimization(neo4j_client, qdrant_client, three_layer_engine))
    # TODO: RecordTrainingFeedback 当前未被DAG/Agent调用，保留注册以备后续训练反馈闭环功能
    registry.register_tool(RecordTrainingFeedback(neo4j_client, qdrant_client, three_layer_engine))
    
    # P2扩展工具（4个）
    registry.register_tool(PeriodizedProgramDesigner(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(TrainingSplitDesigner(neo4j_client, qdrant_client, three_layer_engine))
    registry.register_tool(PosturalAssessor(neo4j_client, qdrant_client, three_layer_engine))
    # TODO: FindSimilarTrainingCases 当前未被DAG/Agent调用，保留注册以备后续相似案例推荐功能
    registry.register_tool(FindSimilarTrainingCasesTool(backend_client, vector_store))


__all__ = [
    # 基类和元数据
    "BaseMCPTool",
    "ToolMetadata",
    # 版本管理 - Requirements 12.1-12.5
    "VersionInfo",
    "ChangelogEntry",
    "MCPToolVersionRegistry",
    "get_version_registry",
    # 三层检索结果 - Requirements 17.1-17.6
    "ThreeLayerQueryResult",
    # 异常类型
    "ToolError",
    "ToolValidationError",
    "ToolTimeoutError",
    "ToolConnectionError",
    "ToolExecutionError",
    # 注册表
    "MCPToolRegistry",
    # 具体工具
    "IntelligentExerciseSelector",
    "ExerciseAlternativeFinder",
    "ContraindicationsChecker",
    "InjuryRiskAssessor",
    "SafeExerciseModifier",
    "MuscleGroupVolumeCalculator",
    "MovementPatternBalancer",
    "IntelligentWeightCalculator",
    "ProfessionalProgramDesigner",
    "PeriodizedProgramDesigner",
    "TrainingSplitDesigner",
    "RecordTrainingFeedback",
    "TDEECalculator",
    "NutritionIntakeAnalyzer",
    "MealPlanDesigner",
    "ExerciseNutritionOptimization",
    "FindSimilarTrainingCasesTool",
    "PosturalAssessor",
    "initialize_all_tools"
]
