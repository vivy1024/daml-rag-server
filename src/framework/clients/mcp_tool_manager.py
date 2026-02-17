"""
MCP工具调用管理器

管理MCP工具的调用、参数验证、结果转换和错误处理。
提供统一的MCP工具调用接口，供MCP编排器使用。

主要特性:
1. 工具调用管理 - 统一的MCP工具调用接口
2. 参数验证 - 确保参数符合MCP协议规范
3. 结果转换 - 将MCP原始结果转换为标准格式
4. 错误处理 - 捕获异常、记录日志、提供降级方案
5. 工具映射 - 任务名称到MCP工具的映射配置
6. 错误统计 - 记录错误次数和类型，用于监控

使用场景:
- 被MCPOrchestrator使用，提供工具调用的统一接口
- 简化MCP工具的参数验证和结果转换
- 提供降级方案，确保系统稳定性

版本: v1.1.0
日期: 2025-12-14
"""

import asyncio
import logging
import traceback
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class MCPToolCallResult:
    """MCP工具调用结果"""
    success: bool
    data: Optional[Dict[str, Any]]
    error: Optional[str]
    tool_name: str
    execution_time_ms: float
    timestamp: datetime
    fallback_used: bool = False
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None


class MCPToolNotFoundError(Exception):
    """MCP工具不存在错误"""
    pass


class MCPToolCallError(Exception):
    """MCP工具调用失败错误"""
    pass


class MCPConnectionError(Exception):
    """MCP连接错误"""
    pass


class MCPTimeoutError(Exception):
    """MCP调用超时错误"""
    pass


class MCPParameterError(Exception):
    """MCP参数错误"""
    pass


@dataclass
class ErrorStatistics:
    """错误统计"""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    fallback_calls: int = 0
    error_by_type: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    error_by_tool: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    last_error_time: Optional[datetime] = None
    last_error_message: Optional[str] = None


class MCPToolManager:
    """
    MCP工具调用管理器
    
    提供统一的MCP工具调用接口，处理参数验证、结果转换和错误恢复。
    供MCPOrchestrator使用，简化MCP工具调用流程。
    """

    def __init__(self, mcp_client=None, python_tool_registry=None):
        """
        初始化MCP工具管理器

        Args:
            mcp_client: MCP客户端实例（可选，如果不提供则需要外部传入server_name和tool_name）
            python_tool_registry: Python内置工具注册表（可选，用于调用本地Python工具）
        """
        # 设置环境变量，消除tokenizers并行化警告
        import os
        os.environ['TOKENIZERS_PARALLELISM'] = 'false'

        self.mcp_client = mcp_client
        self.python_tool_registry = python_tool_registry
        self.tool_mapping = self._load_tool_mapping()
        self.logger = logger
        self.error_stats = ErrorStatistics()

        # 缓存由MCPOrchestrator统一管理，此处不再重复缓存

        # 初始化性能监控
        self.performance_stats = {
            'total_calls': 0,
            'total_duration_ms': 0,
            'by_tool': defaultdict(lambda: {
                'calls': 0,
                'total_duration_ms': 0,
                'min_duration_ms': float('inf'),
                'max_duration_ms': 0,
                'success_count': 0,
                'error_count': 0
            })
        }

    def _load_tool_mapping(self) -> Dict[str, Dict[str, Any]]:
        """
        加载工具映射配置
        
        基于16个已实现的MCP工具（参考：docs/04-开发指南/22-MCP工具集成状态.md）
        
        ⚠️ 重要：required_params必须与工具的Pydantic Input Schema完全匹配！
        
        Returns:
            Dict[str, Dict[str, Any]]: 任务名称到MCP工具的映射表
        """
        # 工具映射表：任务名称 -> MCP工具配置
        # ⚠️ v3.0.27: 同步所有工具的required_params与实际Pydantic Schema
        return {
            # ========== 用户档案工具（1个）==========
            "get_user_profile": {
                "server_name": "user-profile-stdio",
                "tool_name": "get_user_profile",
                "description": "获取用户档案",
                "required_params": ["user_id"],
                "optional_params": [],
                "param_schema": {
                    "user_id": "int"
                }
            },
            
            # ========== P0核心工具（5个）==========
            # IntelligentExerciseSelectorInput: user_id, muscle_group, training_goal, difficulty_level
            "intelligent_exercise_selector": {
                "server_name": "python_internal",
                "tool_name": "intelligent_exercise_selector",
                "description": "智能选择动作",
                "required_params": ["user_id", "muscle_group", "training_goal", "difficulty_level"],
                "optional_params": ["available_equipment", "safety_priority", "injury_history", "exercise_preferences", "disliked_exercises", "session_focus"],
                "param_schema": {
                    "user_id": "str",
                    "muscle_group": "str",
                    "training_goal": "str",
                    "difficulty_level": "str",
                    "available_equipment": "list",
                    "safety_priority": "float"
                }
            },
            
            # ContraindicationsCheckerInput: user_id, exercise_ids
            "contraindications_checker": {
                "server_name": "python_internal",
                "tool_name": "contraindications_checker",
                "description": "检查用户的健康禁忌症",
                "required_params": ["user_id", "exercise_ids"],
                "optional_params": ["health_conditions", "include_recommendations", "strict_mode"],
                "param_schema": {
                    "user_id": "str",
                    "exercise_ids": "list",
                    "health_conditions": "list",
                    "include_recommendations": "bool",
                    "strict_mode": "bool"
                }
            },

            # PosturalAssessorInput: user_id
            "postural_assessor": {
                "server_name": "python_internal",
                "tool_name": "postural_assessor",
                "description": "体态评估与矫正建议",
                "required_params": ["user_id"],
                "optional_params": ["postural_issues", "include_exercises", "max_exercises_per_issue"],
                "param_schema": {
                    "user_id": "str",
                    "postural_issues": "list",
                    "include_exercises": "bool",
                    "max_exercises_per_issue": "int"
                }
            },
            
            # InjuryRiskAssessorInput: user_id, planned_exercises, training_intensity, session_duration_minutes
            "injury_risk_assessor": {
                "server_name": "python_internal",
                "tool_name": "injury_risk_assessor",
                "description": "评估动作的受伤风险",
                "required_params": ["user_id", "planned_exercises", "training_intensity", "session_duration_minutes"],
                "optional_params": ["include_prevention_plan", "risk_tolerance_level", "previous_injuries", "current_pain_areas"],
                "param_schema": {
                    "user_id": "str",
                    "planned_exercises": "list",
                    "training_intensity": "str",
                    "session_duration_minutes": "int",
                    "include_prevention_plan": "bool",
                    "risk_tolerance_level": "str",
                    "previous_injuries": "list",
                    "current_pain_areas": "list"
                }
            },
            
            # MuscleGroupVolumeCalculatorInput: user_id, muscle_group, training_goal, training_frequency_per_week
            "muscle_group_volume_calculator": {
                "server_name": "python_internal",
                "tool_name": "muscle_group_volume_calculator",
                "description": "计算肌群训练量",
                "required_params": ["user_id", "muscle_group", "training_goal", "training_frequency_per_week"],
                "optional_params": ["current_weekly_sets", "recovery_capacity"],
                "param_schema": {
                    "user_id": "str",
                    "muscle_group": "str",
                    "training_goal": "str",
                    "training_frequency_per_week": "int",
                    "current_weekly_sets": "int",
                    "recovery_capacity": "str"
                }
            },
            
            # TDEECalculatorInput: user_id, training_frequency_per_week, training_intensity, daily_activity_level, fitness_goal
            "tdee_calculator": {
                "server_name": "python_internal",
                "tool_name": "tdee_calculator",
                "description": "计算每日总能量消耗",
                "required_params": ["user_id", "training_frequency_per_week", "training_intensity", "daily_activity_level", "fitness_goal"],
                "optional_params": ["age", "gender", "weight_kg", "height_cm", "dietary_preference"],
                "param_schema": {
                    "user_id": "str",
                    "training_frequency_per_week": "int",
                    "training_intensity": "str",
                    "daily_activity_level": "str",
                    "fitness_goal": "str",
                    "age": "int",
                    "gender": "str",
                    "weight_kg": "float",
                    "height_cm": "float",
                    "dietary_preference": "str"
                }
            },
            
            # ========== P1建议工具（8个）==========
            # ProfessionalProgramDesignerInput: user_id, training_goal, training_split, training_days_per_week, difficulty_level, available_equipment
            "professional_program_designer": {
                "server_name": "python_internal",
                "tool_name": "professional_program_designer",
                "description": "专业训练计划设计",
                "required_params": ["user_id", "training_goal", "training_split", "training_days_per_week", "difficulty_level", "available_equipment"],
                "optional_params": ["injury_history", "target_muscle_groups"],
                "param_schema": {
                    "user_id": "str",
                    "training_goal": "str",
                    "training_split": "str",
                    "training_days_per_week": "int",
                    "difficulty_level": "str",
                    "available_equipment": "list",
                    "injury_history": "list",
                    "target_muscle_groups": "list"
                }
            },
            
            # ExerciseAlternativeFinderInput: user_id, original_exercise_id, reason
            "exercise_alternative_finder": {
                "server_name": "python_internal",
                "tool_name": "exercise_alternative_finder",
                "description": "查找替代动作",
                "required_params": ["user_id", "original_exercise_id", "reason"],
                "optional_params": ["constraints"],
                "param_schema": {
                    "user_id": "str",
                    "original_exercise_id": "str",
                    "reason": "str",
                    "constraints": "dict"
                }
            },
            
            # MovementPatternBalancerInput: user_id, current_program, target_muscle_groups
            "movement_pattern_balancer": {
                "server_name": "python_internal",
                "tool_name": "movement_pattern_balancer",
                "description": "平衡动作模式",
                "required_params": ["user_id", "current_program", "target_muscle_groups"],
                "optional_params": [],
                "param_schema": {
                    "user_id": "str",
                    "current_program": "list",
                    "target_muscle_groups": "list"
                }
            },
            
            # IntelligentWeightCalculatorInput: user_id, exercise_id
            "intelligent_weight_calculator": {
                "server_name": "python_internal",
                "tool_name": "intelligent_weight_calculator",
                "description": "智能计算训练重量",
                "required_params": ["user_id", "exercise_id"],
                "optional_params": ["training_goal", "target_reps", "target_rir", "one_rm", "recent_performance"],
                "param_schema": {
                    "user_id": "str",
                    "exercise_id": "str",
                    "training_goal": "str",
                    "target_reps": "int",
                    "target_rir": "int",
                    "one_rm": "float",
                    "recent_performance": "dict"
                }
            },
            
            # SafeExerciseModifierInput: user_id, exercise_id, modification_purpose
            "safe_exercise_modifier": {
                "server_name": "python_internal",
                "tool_name": "safe_exercise_modifier",
                "description": "安全修改动作",
                "required_params": ["user_id", "exercise_id", "modification_purpose"],
                "optional_params": ["user_injuries", "safety_requirements", "available_equipment", "modification_preference"],
                "param_schema": {
                    "user_id": "str",
                    "exercise_id": "str",
                    "modification_purpose": "str",
                    "user_injuries": "list",
                    "safety_requirements": "list",
                    "available_equipment": "list",
                    "modification_preference": "str"
                }
            },
            
            # NutritionIntakeAnalyzerInput: user_id, daily_food_intake
            "nutrition_intake_analyzer": {
                "server_name": "python_internal",
                "tool_name": "nutrition_intake_analyzer",
                "description": "分析营养摄入",
                "required_params": ["user_id", "daily_food_intake"],
                "optional_params": ["target_calories", "target_protein_grams", "target_carbs_grams", "target_fat_grams", "include_micronutrients", "fitness_goal"],
                "param_schema": {
                    "user_id": "str",
                    "daily_food_intake": "list",
                    "target_calories": "float",
                    "target_protein_grams": "float",
                    "target_carbs_grams": "float",
                    "target_fat_grams": "float",
                    "include_micronutrients": "bool",
                    "fitness_goal": "str"
                }
            },
            
            # MealPlanDesignerInput: user_id, target_calories, target_protein_grams, target_carbs_grams, target_fat_grams
            "meal_plan_designer": {
                "server_name": "python_internal",
                "tool_name": "meal_plan_designer",
                "description": "膳食计划设计",
                "required_params": ["user_id", "target_calories", "target_protein_grams", "target_carbs_grams", "target_fat_grams"],
                "optional_params": ["dietary_preference", "meals_per_day", "training_days_per_week", "fitness_goal"],
                "param_schema": {
                    "user_id": "str",
                    "target_calories": "float",
                    "target_protein_grams": "float",
                    "target_carbs_grams": "float",
                    "target_fat_grams": "float",
                    "dietary_preference": "str",
                    "meals_per_day": "int",
                    "training_days_per_week": "int",
                    "fitness_goal": "str"
                }
            },
            
            # ExerciseNutritionOptimizationInput: user_id, training_type, training_duration_minutes, training_intensity, training_time, weight_kg, fitness_goal, daily_protein_target, daily_carbs_target
            "exercise_nutrition_optimization": {
                "server_name": "python_internal",
                "tool_name": "exercise_nutrition_optimization",
                "description": "优化运动营养",
                "required_params": ["user_id", "training_type", "training_duration_minutes", "training_intensity", "training_time", "weight_kg", "fitness_goal", "daily_protein_target", "daily_carbs_target"],
                "optional_params": ["current_supplements"],
                "param_schema": {
                    "user_id": "str",
                    "training_type": "str",
                    "training_duration_minutes": "int",
                    "training_intensity": "str",
                    "training_time": "str",
                    "weight_kg": "float",
                    "fitness_goal": "str",
                    "daily_protein_target": "float",
                    "daily_carbs_target": "float",
                    "current_supplements": "list"
                }
            },
            
            # ========== P2扩展工具（2个已实现）==========
            # PeriodizedProgramDesignerInput: user_id, training_goal, difficulty_level, program_duration_weeks, training_days_per_week, available_equipment
            "periodized_program_designer": {
                "server_name": "python_internal",
                "tool_name": "periodized_program_designer",
                "description": "周期化训练计划设计",
                "required_params": ["user_id", "training_goal", "difficulty_level", "program_duration_weeks", "training_days_per_week", "available_equipment"],
                "optional_params": ["injury_history", "target_muscle_groups", "periodization_model", "include_deload_weeks", "auto_progression"],
                "param_schema": {
                    "user_id": "str",
                    "training_goal": "str",
                    "difficulty_level": "str",
                    "program_duration_weeks": "int",
                    "training_days_per_week": "int",
                    "available_equipment": "list",
                    "injury_history": "list",
                    "target_muscle_groups": "list",
                    "periodization_model": "str",
                    "include_deload_weeks": "bool",
                    "auto_progression": "bool"
                }
            },
            
            # TrainingSplitDesignerInput: user_id, training_level, primary_goal, training_days_per_week, session_duration_minutes, available_equipment
            "training_split_designer": {
                "server_name": "python_internal",
                "tool_name": "training_split_designer",
                "description": "训练分化设计",
                "required_params": ["user_id", "training_level", "primary_goal", "training_days_per_week", "session_duration_minutes", "available_equipment"],
                "optional_params": ["muscle_group_focus", "injury_history", "preferred_split_type", "include_cardio", "rest_day_preference", "time_constraints"],
                "param_schema": {
                    "user_id": "str",
                    "training_level": "str",
                    "primary_goal": "str",
                    "training_days_per_week": "int",
                    "session_duration_minutes": "int",
                    "available_equipment": "list",
                    "muscle_group_focus": "list",
                    "injury_history": "list",
                    "preferred_split_type": "str",
                    "include_cardio": "bool",
                    "rest_day_preference": "str",
                    "time_constraints": "str"
                }
            },
            
            # ========== 训练案例库工具（1个）==========
            # FindSimilarTrainingCasesInput: query, user_profile
            "find_similar_training_cases": {
                "server_name": "python_internal",
                "tool_name": "find_similar_training_cases",
                "description": "查找相似的训练案例，基于质量评分和用户特征推荐成功案例",
                "required_params": ["query", "user_profile"],
                "optional_params": ["training_goal", "min_quality_score", "training_effect_filter", "top_k"],
                "param_schema": {
                    "query": "str",
                    "user_profile": "dict",
                    "training_goal": "str",
                    "min_quality_score": "float",
                    "training_effect_filter": "str",
                    "top_k": "int"
                }
            },
            
        }

    async def call_tool_with_retry(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        mcp_client=None,
        context: Optional[Dict[str, Any]] = None,
        max_retries: int = 2
    ) -> MCPToolCallResult:
        """
        调用MCP工具（带重试机制）
        
        Args:
            task_name: 任务名称
            parameters: 工具参数
            mcp_client: MCP客户端实例（可选）
            context: 执行上下文（可选）
            max_retries: 最大重试次数（默认2次）
        
        Returns:
            MCPToolCallResult: 标准化的工具调用结果
        """
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                # 调用原始的call_tool方法
                result = await self._call_tool_impl(
                    task_name=task_name,
                    parameters=parameters,
                    mcp_client=mcp_client,
                    context=context
                )
                
                # 如果成功，返回结果
                if result.success:
                    if attempt > 0:
                        self.logger.info(
                            f"✅ MCP工具调用成功（重试{attempt}次后）: {task_name}"
                        )
                    return result
                
                # 如果失败但不是最后一次尝试，继续重试
                if attempt < max_retries:
                    last_error = result.error
                    wait_time = (attempt + 1) * 1  # 指数退避：1秒、2秒
                    self.logger.warning(
                        f"⚠️ MCP工具调用失败，{wait_time}秒后重试 "
                        f"({attempt + 1}/{max_retries}): {task_name}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    # 最后一次尝试也失败了
                    self.logger.error(
                        f"❌ MCP工具调用失败，已达最大重试次数 "
                        f"({max_retries}次): {task_name}"
                    )
                    return result
                    
            except Exception as e:
                last_error = str(e)
                
                if attempt < max_retries:
                    wait_time = (attempt + 1) * 1  # 指数退避
                    self.logger.warning(
                        f"⚠️ MCP工具调用异常，{wait_time}秒后重试 "
                        f"({attempt + 1}/{max_retries}): {task_name}\n"
                        f"   错误: {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        f"❌ MCP工具调用异常，已达最大重试次数 "
                        f"({max_retries}次): {task_name}\n"
                        f"   错误: {str(e)}"
                    )
                    # 返回失败结果
                    return MCPToolCallResult(
                        success=False,
                        data=None,
                        error=str(e),
                        tool_name=task_name,
                        execution_time_ms=0,
                        timestamp=datetime.now(),
                        fallback_used=False,
                        error_type=type(e).__name__,
                        stack_trace=traceback.format_exc()
                    )
        
        # 理论上不会到达这里
        return MCPToolCallResult(
            success=False,
            data=None,
            error=last_error or "未知错误",
            tool_name=task_name,
            execution_time_ms=0,
            timestamp=datetime.now(),
            fallback_used=False,
            error_type="UnknownError",
            stack_trace=None
        )

    async def _call_tool_impl(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        mcp_client=None,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolCallResult:
        """
        内部实现：调用MCP工具（不带重试）
        
        这是原来的call_tool方法的实现，现在作为内部方法供call_tool_with_retry使用
        """
        start_time = datetime.now()
        self.error_stats.total_calls += 1
        
        # 使用传入的客户端或初始化时的客户端
        client = mcp_client or self.mcp_client
        
        try:
            # 检查工具是否存在
            if task_name not in self.tool_mapping:
                error_msg = (
                    f"未知的MCP工具任务: {task_name}\n"
                    f"已知任务: {list(self.tool_mapping.keys())}\n"
                    f"请在tool_mapping中添加该任务的配置"
                )
                self.logger.error(error_msg)
                self._record_error("MCPToolNotFoundError", task_name, error_msg)
                raise MCPToolNotFoundError(error_msg)
            
            tool_config = self.tool_mapping[task_name]
            server_name = tool_config["server_name"]
            tool_name = tool_config["tool_name"]
            
            self.logger.info(
                f"🔧 调用MCP工具: {task_name} -> "
                f"{server_name}/{tool_name}"
            )
            
            # 验证参数
            if not self._validate_parameters(task_name, parameters):
                error_msg = f"参数验证失败: {task_name}"
                self.logger.error(error_msg)
                self._record_error("MCPParameterError", task_name, error_msg)
                raise MCPParameterError(error_msg)
            
            # 判断是Python内置工具还是MCP工具
            if server_name == "python_internal":
                # Python内置工具：直接调用MCPToolRegistry
                if not self.python_tool_registry:
                    error_msg = f"Python工具注册表未初始化: {task_name}"
                    self.logger.error(error_msg)
                    self._record_error("MCPToolNotFoundError", task_name, error_msg)
                    raise MCPToolNotFoundError(error_msg)
                
                self.logger.debug(f"   → 调用Python内置工具: {tool_name}")
                raw_result = await self.python_tool_registry.call_tool(
                    tool_name=tool_name,
                    input_data=parameters
                )
            else:
                # MCP工具：通过MCP客户端调用
                if client:
                    raw_result = await client.call_tool(
                        server_name=server_name,
                        tool_name=tool_name,
                        arguments=parameters
                    )
                else:
                    # 如果没有客户端，返回模拟结果
                    self.logger.warning(f"⚠️ 没有MCP客户端，返回模拟结果: {task_name}")
                    raw_result = {
                        "success": True,
                        "data": {"message": "模拟结果（无MCP客户端）"},
                        "tool_name": tool_name
                    }
            
            # 转换结果
            converted_result = self._convert_result(raw_result, tool_name)
            
            # 计算执行时间
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            
            self.logger.info(
                f"✅ MCP工具调用成功: {task_name} "
                f"(耗时: {execution_time:.2f}ms)"
            )
            
            self.error_stats.successful_calls += 1
            
            # 记录性能指标
            self._record_performance(task_name, execution_time, success=True)
            
            return MCPToolCallResult(
                success=True,
                data=converted_result,
                error=None,
                tool_name=tool_name,
                execution_time_ms=execution_time,
                timestamp=datetime.now(),
                fallback_used=False,
                error_type=None,
                stack_trace=None
            )
            
        except MCPToolNotFoundError:
            # 工具不存在，直接抛出（不提供降级）
            raise
            
        except MCPParameterError:
            # 参数错误，直接抛出（不提供降级）
            raise
            
        except asyncio.TimeoutError as e:
            # 超时错误
            return self._handle_timeout_error(task_name, parameters, e, start_time)
            
        except ConnectionError as e:
            # 连接错误
            return self._handle_connection_error(task_name, parameters, e, start_time)
            
        except Exception as e:
            # 其他错误，记录详细日志并提供降级方案
            return self._handle_general_error(task_name, parameters, e, start_time)

    async def call_tool(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        mcp_client=None,
        context: Optional[Dict[str, Any]] = None
    ) -> MCPToolCallResult:
        """
        调用MCP工具（带重试）

        这是主要的公共接口，提供重试功能。

        Args:
            task_name: 任务名称（如 "check_contraindications"）
            parameters: 工具参数
            mcp_client: MCP客户端实例（可选，如果初始化时未提供）
            context: 执行上下文（可选）

        Returns:
            MCPToolCallResult: 标准化的工具调用结果

        Raises:
            MCPToolNotFoundError: 工具不存在
        """
        # 缓存由MCPOrchestrator统一管理，此处不再重复缓存

        # 调用工具（带重试）
        result = await self.call_tool_with_retry(
            task_name=task_name,
            parameters=parameters,
            mcp_client=mcp_client,
            context=context,
            max_retries=2
        )

        return result

    def _handle_timeout_error(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        error: Exception,
        start_time: datetime
    ) -> MCPToolCallResult:
        """
        处理超时错误
        
        Args:
            task_name: 任务名称
            parameters: 参数
            error: 异常对象
            start_time: 开始时间
        
        Returns:
            MCPToolCallResult: 包含降级结果的调用结果
        """
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        tool_config = self.tool_mapping.get(task_name, {})
        error_msg = f"MCP工具调用超时: {task_name}"
        stack_trace = traceback.format_exc()
        
        self.logger.error(
            f"⏱️ {error_msg}\n"
            f"   工具名: {tool_config.get('tool_name', 'unknown')}\n"
            f"   服务器: {tool_config.get('server_name', 'unknown')}\n"
            f"   参数: {parameters}\n"
            f"   超时时间: {execution_time:.2f}ms\n"
            f"   错误详情: {str(error)}\n"
            f"   堆栈跟踪:\n{stack_trace}"
        )
        
        self._record_error("MCPTimeoutError", task_name, error_msg)
        
        # 记录性能指标
        self._record_performance(task_name, execution_time, success=False)
        
        # 提供降级方案
        fallback_result = self._get_fallback_result(
            task_name, 
            parameters, 
            error_msg,
            "timeout"
        )
        
        return MCPToolCallResult(
            success=False,
            data=fallback_result,
            error=error_msg,
            tool_name=tool_config.get("tool_name", "unknown"),
            execution_time_ms=execution_time,
            timestamp=datetime.now(),
            fallback_used=True,
            error_type="MCPTimeoutError",
            stack_trace=stack_trace
        )

    def _handle_connection_error(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        error: Exception,
        start_time: datetime
    ) -> MCPToolCallResult:
        """
        处理连接错误
        
        Args:
            task_name: 任务名称
            parameters: 参数
            error: 异常对象
            start_time: 开始时间
        
        Returns:
            MCPToolCallResult: 包含降级结果的调用结果
        """
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        tool_config = self.tool_mapping.get(task_name, {})
        error_msg = f"MCP服务连接失败: {task_name}"
        stack_trace = traceback.format_exc()
        
        self.logger.error(
            f"🔌 {error_msg}\n"
            f"   工具名: {tool_config.get('tool_name', 'unknown')}\n"
            f"   服务器: {tool_config.get('server_name', 'unknown')}\n"
            f"   参数: {parameters}\n"
            f"   错误详情: {str(error)}\n"
            f"   堆栈跟踪:\n{stack_trace}\n"
            f"   建议: 请检查MCP服务器是否正常运行"
        )
        
        self._record_error("MCPConnectionError", task_name, error_msg)
        
        # 记录性能指标
        self._record_performance(task_name, execution_time, success=False)
        
        # 提供降级方案
        fallback_result = self._get_fallback_result(
            task_name, 
            parameters, 
            error_msg,
            "connection"
        )
        
        return MCPToolCallResult(
            success=False,
            data=fallback_result,
            error=error_msg,
            tool_name=tool_config.get("tool_name", "unknown"),
            execution_time_ms=execution_time,
            timestamp=datetime.now(),
            fallback_used=True,
            error_type="MCPConnectionError",
            stack_trace=stack_trace
        )

    def _handle_general_error(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        error: Exception,
        start_time: datetime
    ) -> MCPToolCallResult:
        """
        处理一般错误
        
        Args:
            task_name: 任务名称
            parameters: 参数
            error: 异常对象
            start_time: 开始时间
        
        Returns:
            MCPToolCallResult: 包含降级结果的调用结果
        """
        execution_time = (datetime.now() - start_time).total_seconds() * 1000
        tool_config = self.tool_mapping.get(task_name, {})
        error_type = type(error).__name__
        error_msg = str(error)
        stack_trace = traceback.format_exc()
        
        self.logger.error(
            f"❌ MCP工具调用失败: {task_name}\n"
            f"   工具名: {tool_config.get('tool_name', 'unknown')}\n"
            f"   服务器: {tool_config.get('server_name', 'unknown')}\n"
            f"   参数: {parameters}\n"
            f"   错误类型: {error_type}\n"
            f"   错误详情: {error_msg}\n"
            f"   堆栈跟踪:\n{stack_trace}"
        )
        
        self._record_error(error_type, task_name, error_msg)
        
        # 记录性能指标
        self._record_performance(task_name, execution_time, success=False)
        
        # 提供降级方案
        fallback_result = self._get_fallback_result(
            task_name, 
            parameters, 
            error_msg,
            "general"
        )
        
        return MCPToolCallResult(
            success=False,
            data=fallback_result,
            error=error_msg,
            tool_name=tool_config.get("tool_name", "unknown"),
            execution_time_ms=execution_time,
            timestamp=datetime.now(),
            fallback_used=True,
            error_type=error_type,
            stack_trace=stack_trace
        )

    def _record_error(self, error_type: str, task_name: str, error_msg: str):
        """
        记录错误统计
        
        Args:
            error_type: 错误类型
            task_name: 任务名称
            error_msg: 错误信息
        """
        self.error_stats.failed_calls += 1
        self.error_stats.error_by_type[error_type] += 1
        self.error_stats.error_by_tool[task_name] += 1
        self.error_stats.last_error_time = datetime.now()
        self.error_stats.last_error_message = error_msg

    def _validate_parameters(
        self,
        task_name: str,
        parameters: Dict[str, Any]
    ) -> bool:
        """
        验证参数是否符合MCP协议规范
        
        Args:
            task_name: 任务名称
            parameters: 工具参数
        
        Returns:
            bool: 参数是否有效
        """
        try:
            tool_config = self.tool_mapping.get(task_name)
            if not tool_config:
                self.logger.error(f"工具配置不存在: {task_name}")
                return False
            
            # 检查必需参数
            required_params = tool_config.get("required_params", [])
            for param in required_params:
                if param not in parameters:
                    self.logger.error(
                        f"缺少必需参数: {param} (任务: {task_name})"
                    )
                    return False
            
            # 检查参数类型（基本验证）
            param_schema = tool_config.get("param_schema", {})
            for param_name, param_value in parameters.items():
                if param_name in param_schema:
                    expected_type = param_schema[param_name]
                    actual_type = type(param_value).__name__
                    
                    # 简单的类型检查
                    if expected_type == "dict" and not isinstance(param_value, dict):
                        self.logger.warning(
                            f"参数类型不匹配: {param_name} "
                            f"(期望: {expected_type}, 实际: {actual_type})"
                        )
                    elif expected_type == "list" and not isinstance(param_value, list):
                        self.logger.warning(
                            f"参数类型不匹配: {param_name} "
                            f"(期望: {expected_type}, 实际: {actual_type})"
                        )
            
            self.logger.debug(f"✅ 参数验证通过: {task_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"参数验证异常: {e}", exc_info=True)
            return False

    def _convert_result(
        self,
        raw_result: Any,
        tool_name: str
    ) -> Dict[str, Any]:
        """
        将MCP原始结果转换为标准格式
        
        Args:
            raw_result: MCP原始结果
            tool_name: 工具名称
        
        Returns:
            Dict[str, Any]: 标准化的结果字典
        """
        try:
            # 如果已经是字典格式，直接返回
            if isinstance(raw_result, dict):
                # 确保包含必需字段
                standardized = {
                    "success": raw_result.get("success", True),
                    "data": raw_result.get("data", raw_result),
                    "error": raw_result.get("error"),
                    "tool_name": tool_name,
                    "timestamp": datetime.now().isoformat()
                }
                return standardized
            
            # 如果是其他类型，包装成字典
            return {
                "success": True,
                "data": raw_result,
                "error": None,
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"结果转换失败: {e}", exc_info=True)
            return {
                "success": False,
                "data": None,
                "error": f"结果转换失败: {str(e)}",
                "tool_name": tool_name,
                "timestamp": datetime.now().isoformat()
            }

    def _get_fallback_result(
        self,
        task_name: str,
        parameters: Dict[str, Any],
        error: str,
        error_category: str = "general"
    ) -> Dict[str, Any]:
        """
        获取降级结果（增强版）
        
        Args:
            task_name: 任务名称
            parameters: 原始参数
            error: 错误信息
            error_category: 错误类别（timeout/connection/general）
        
        Returns:
            Dict[str, Any]: 降级结果
        """
        self.error_stats.fallback_calls += 1
        
        # 根据错误类别提供不同的降级建议
        fallback_messages = {
            "timeout": f"MCP工具 {task_name} 响应超时，请稍后重试或联系管理员",
            "connection": f"MCP服务 {task_name} 暂时无法连接，请检查服务状态",
            "general": f"MCP工具 {task_name} 暂时不可用，请稍后重试"
        }
        
        return {
            "success": False,
            "data": None,
            "error": error,
            "fallback": True,
            "error_category": error_category,
            "task_name": task_name,
            "message": fallback_messages.get(error_category, fallback_messages["general"]),
            "timestamp": datetime.now().isoformat(),
            "suggestion": self._get_error_suggestion(error_category)
        }

    def _get_error_suggestion(self, error_category: str) -> str:
        """
        获取错误建议
        
        Args:
            error_category: 错误类别
        
        Returns:
            str: 错误建议
        """
        suggestions = {
            "timeout": "建议：1) 检查网络连接 2) 增加超时时间 3) 检查MCP服务负载",
            "connection": "建议：1) 确认MCP服务正在运行 2) 检查服务端口 3) 查看服务日志",
            "general": "建议：1) 查看详细错误日志 2) 检查参数格式 3) 联系技术支持"
        }
        return suggestions.get(error_category, suggestions["general"])

    def get_tool_info(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        获取工具信息
        
        Args:
            task_name: 任务名称
        
        Returns:
            Optional[Dict[str, Any]]: 工具配置信息
        """
        return self.tool_mapping.get(task_name)

    def list_available_tools(self) -> List[str]:
        """
        列出所有可用的工具
        
        Returns:
            List[str]: 工具名称列表
        """
        return list(self.tool_mapping.keys())

    def get_tool_mapping(self) -> Dict[str, Dict[str, Any]]:
        """
        获取完整的工具映射表
        
        Returns:
            Dict[str, Dict[str, Any]]: 工具映射表
        """
        return self.tool_mapping.copy()

    def get_error_statistics(self) -> Dict[str, Any]:
        """
        获取错误统计信息
        
        Returns:
            Dict[str, Any]: 错误统计
        """
        success_rate = (
            self.error_stats.successful_calls / self.error_stats.total_calls * 100
            if self.error_stats.total_calls > 0 else 0
        )
        
        return {
            "total_calls": self.error_stats.total_calls,
            "successful_calls": self.error_stats.successful_calls,
            "failed_calls": self.error_stats.failed_calls,
            "fallback_calls": self.error_stats.fallback_calls,
            "success_rate": f"{success_rate:.2f}%",
            "error_by_type": dict(self.error_stats.error_by_type),
            "error_by_tool": dict(self.error_stats.error_by_tool),
            "last_error_time": (
                self.error_stats.last_error_time.isoformat()
                if self.error_stats.last_error_time else None
            ),
            "last_error_message": self.error_stats.last_error_message
        }

    def reset_error_statistics(self):
        """重置错误统计"""
        self.error_stats = ErrorStatistics()
        self.logger.info("🔄 错误统计已重置")

    # 缓存由MCPOrchestrator统一管理，此处不再重复缓存

    def _record_performance(self, task_name: str, duration_ms: float, success: bool):
        """
        记录性能指标
        
        Args:
            task_name: 任务名称
            duration_ms: 执行时间（毫秒）
            success: 是否成功
        """
        # 更新总体统计
        self.performance_stats['total_calls'] += 1
        self.performance_stats['total_duration_ms'] += duration_ms
        
        # 更新工具级别统计
        tool_stats = self.performance_stats['by_tool'][task_name]
        tool_stats['calls'] += 1
        tool_stats['total_duration_ms'] += duration_ms
        tool_stats['min_duration_ms'] = min(tool_stats['min_duration_ms'], duration_ms)
        tool_stats['max_duration_ms'] = max(tool_stats['max_duration_ms'], duration_ms)
        
        if success:
            tool_stats['success_count'] += 1
        else:
            tool_stats['error_count'] += 1

    def get_performance_statistics(self) -> Dict[str, Any]:
        """
        获取性能统计信息
        
        Returns:
            Dict[str, Any]: 性能统计
        """
        total_calls = self.performance_stats['total_calls']
        total_duration = self.performance_stats['total_duration_ms']
        
        # 计算平均耗时
        avg_duration = total_duration / total_calls if total_calls > 0 else 0
        
        # 按工具统计
        by_tool = {}
        for tool_name, stats in self.performance_stats['by_tool'].items():
            calls = stats['calls']
            avg_tool_duration = stats['total_duration_ms'] / calls if calls > 0 else 0
            success_rate = (stats['success_count'] / calls * 100) if calls > 0 else 0
            
            by_tool[tool_name] = {
                'calls': calls,
                'avg_duration_ms': round(avg_tool_duration, 2),
                'min_duration_ms': round(stats['min_duration_ms'], 2) if stats['min_duration_ms'] != float('inf') else 0,
                'max_duration_ms': round(stats['max_duration_ms'], 2),
                'success_rate': f"{success_rate:.2f}%",
                'success_count': stats['success_count'],
                'error_count': stats['error_count']
            }
        
        return {
            'total_calls': total_calls,
            'total_duration_ms': round(total_duration, 2),
            'avg_duration_ms': round(avg_duration, 2),
            'by_tool': by_tool
        }

    def send_metrics_to_prometheus(self):
        """
        发送指标到Prometheus
        
        注意：这需要prometheus_client库支持
        """
        try:
            from prometheus_client import Counter, Histogram, Gauge
            
            # 定义指标（如果还没有定义）
            if not hasattr(self, '_prometheus_metrics_defined'):
                # MCP工具调用次数
                self.mcp_tool_calls_total = Counter(
                    'mcp_tool_calls_total',
                    'Total number of MCP tool calls',
                    ['tool_name', 'status']
                )

                # MCP工具调用耗时
                self.mcp_tool_duration_seconds = Histogram(
                    'mcp_tool_duration_seconds',
                    'MCP tool call duration in seconds',
                    ['tool_name']
                )

                # 缓存由MCPOrchestrator统一管理，此处不再定义缓存指标

                self._prometheus_metrics_defined = True
            
            # 更新指标
            for tool_name, stats in self.performance_stats['by_tool'].items():
                # 记录成功和失败次数
                self.mcp_tool_calls_total.labels(
                    tool_name=tool_name,
                    status='success'
                ).inc(stats['success_count'])
                
                self.mcp_tool_calls_total.labels(
                    tool_name=tool_name,
                    status='error'
                ).inc(stats['error_count'])
                
                # 记录耗时（转换为秒）
                avg_duration_seconds = stats['total_duration_ms'] / 1000 / stats['calls'] if stats['calls'] > 0 else 0
                self.mcp_tool_duration_seconds.labels(
                    tool_name=tool_name
                ).observe(avg_duration_seconds)

            # 缓存由MCPOrchestrator统一管理，此处不再记录缓存命中率

            self.logger.debug("📊 已发送指标到Prometheus")
            
        except ImportError:
            self.logger.warning("⚠️ prometheus_client未安装，无法发送指标")
        except Exception as e:
            self.logger.error(f"❌ 发送Prometheus指标失败: {e}")

    def reset_performance_statistics(self):
        """重置性能统计"""
        self.performance_stats = {
            'total_calls': 0,
            'total_duration_ms': 0,
            'by_tool': defaultdict(lambda: {
                'calls': 0,
                'total_duration_ms': 0,
                'min_duration_ms': float('inf'),
                'max_duration_ms': 0,
                'success_count': 0,
                'error_count': 0
            })
        }
        self.logger.info("🔄 性能统计已重置")


# 便捷工厂函数
def create_mcp_tool_manager(mcp_client=None, python_tool_registry=None) -> MCPToolManager:
    """
    创建MCP工具管理器
    
    Args:
        mcp_client: MCP客户端实例（可选）
        python_tool_registry: Python内置工具注册表（可选）
    
    Returns:
        MCPToolManager: MCP工具管理器实例
    """
    return MCPToolManager(mcp_client, python_tool_registry)
