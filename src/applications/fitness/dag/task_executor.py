# -*- coding: utf-8 -*-
"""
DAG任务执行器

负责单个DAG任务的执行，包括：
1. 参数增强和处理
2. 缓存检查和存储
3. 重试机制
4. MCP工具调用

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-28
"""

import asyncio
import logging
import time
import json
import hashlib
from typing import Dict, List, Optional, Any

from .models import DAGTask, TaskStatus

logger = logging.getLogger(__name__)


class TaskParamBuilder:
    """
    任务参数构建器
    
    根据工具类型构建相应的参数。
    """

    def __init__(self, user_profile: Dict[str, Any], session_context: Dict[str, Any] = None):
        self.user_profile = user_profile
        self.session_context = session_context or {}

    def _get_primary_goal(self, default: str = "general_fitness") -> str:
        """
        获取主要健身目标

        从 fitness_goals.primary_goal 提取英文枚举值（hypertrophy/fat_loss 等）。
        """
        fitness_goals = self.user_profile.get("fitness_goals", {})

        if isinstance(fitness_goals, dict):
            primary_goal = fitness_goals.get("primary_goal", "")
            if primary_goal:
                return primary_goal

        return default

    def build_params(self, tool_name: str) -> Dict[str, Any]:
        """构建工具参数"""
        base_params = {
            "user_id": self.user_profile.get("user_id"),
            "user_profile": self.user_profile
        }

        param_builders = {
            "intelligent_exercise_selector": self._build_exercise_selector_params,
            "professional_program_designer": self._build_program_designer_params,
            "periodized_program_designer": self._build_periodized_program_params,
            "training_split_designer": self._build_training_split_params,
            "meal_plan_designer": self._build_meal_plan_params,
            "muscle_group_volume_calculator": self._build_volume_calculator_params,
            "training_analytics_dashboard": self._build_analytics_params,
            "contraindications_checker": self._build_contraindications_params,
            "injury_risk_assessor": self._build_injury_risk_params,
            "movement_pattern_balancer": self._build_movement_pattern_params,
            "tdee_calculator": self._build_tdee_params,
            "safe_exercise_modifier": self._build_safe_exercise_modifier_params,
            "exercise_alternative_finder": self._build_exercise_alternative_params,
            "nutrition_intake_analyzer": self._build_nutrition_intake_params,
            "exercise_nutrition_optimization": self._build_exercise_nutrition_params,
        }

        if tool_name in param_builders:
            base_params.update(param_builders[tool_name]())

        return base_params

    def _build_exercise_selector_params(self) -> Dict[str, Any]:
        """构建动作选择器参数"""
        target_muscles = self.user_profile.get("target_muscle_groups", [])
        muscle_group = target_muscles[0] if isinstance(target_muscles, list) and target_muscles else "chest"
        
        # 使用统一的目标获取方法
        training_goal = self._get_primary_goal("hypertrophy")
        
        return {
            "muscle_group": muscle_group,
            "training_goal": training_goal,
            "available_equipment": self.user_profile.get("available_equipment", []),
            "difficulty_level": self.user_profile.get("fitness_level", "beginner"),
            "safety_priority": True
        }

    def _build_program_designer_params(self) -> Dict[str, Any]:
        """构建程序设计师参数"""
        # 使用统一的目标获取方法
        training_goal = self._get_primary_goal("hypertrophy")
        
        training_days = self.user_profile.get("preferred_training_days", 3)
        
        # 优先使用用户档案中的偏好分化类型
        fitness_config = self.user_profile.get("fitness_config", {})
        preferred_split = fitness_config.get("preferred_split_type")
        preferred_rest_pattern = fitness_config.get("preferred_rest_pattern")
        
        # 如果没有偏好，根据训练天数自动映射
        if preferred_split:
            training_split = preferred_split
        else:
            split_mapping = {
                1: "full_body", 2: "upper_lower", 3: "push_pull_legs",
                4: "upper_lower", 5: "push_pull_legs", 6: "push_pull_legs", 7: "bro_split"
            }
            training_split = split_mapping.get(training_days, "push_pull_legs")
        
        return {
            "training_goal": training_goal,
            "training_split": training_split,
            "training_days_per_week": training_days,
            "difficulty_level": self.user_profile.get("fitness_level", "beginner"),
            "available_equipment": self.user_profile.get("available_equipment", []),
            "injury_history": self.user_profile.get("injury_history", []),
            "target_muscle_groups": self.user_profile.get("target_muscle_groups", []),
            "session_duration_minutes": self.user_profile.get("session_duration", 60),
            "rest_pattern": preferred_rest_pattern  # 传递休息模式
        }

    def _build_periodized_program_params(self) -> Dict[str, Any]:
        """构建周期化训练计划参数"""
        # 使用统一的目标获取方法
        training_goal = self._get_primary_goal("hypertrophy")
        
        return {
            "training_goal": training_goal,
            "difficulty_level": self.user_profile.get("fitness_level", "beginner"),
            "program_duration_weeks": 12,
            "training_days_per_week": self.user_profile.get("preferred_training_days", 3),
            "available_equipment": self.user_profile.get("available_equipment", []),
            "injury_history": self.user_profile.get("injury_history", []),
            "target_muscle_groups": self.user_profile.get("target_muscle_groups", []),
            "include_deload_weeks": True,
            "auto_progression": True
        }

    def _build_training_split_params(self) -> Dict[str, Any]:
        """构建训练分化参数"""
        # 使用统一的目标获取方法
        training_goal = self._get_primary_goal("hypertrophy")
        
        return {
            "training_level": self.user_profile.get("fitness_level", "beginner"),
            "primary_goal": training_goal,
            "training_days_per_week": self.user_profile.get("preferred_training_days", 3),
            "session_duration_minutes": self.user_profile.get("session_duration", 60),
            "available_equipment": self.user_profile.get("available_equipment", []),
            "muscle_group_focus": self.user_profile.get("target_muscle_groups", []),
            "injury_history": self.user_profile.get("injury_history", []),
            "include_cardio": self.user_profile.get("include_cardio", True),
            "rest_day_preference": "spread_out"
        }

    def _build_contraindications_params(self) -> Dict[str, Any]:
        """构建禁忌症检查参数"""
        return {
            "user_id": self.user_profile.get("user_id"),
            "exercise_ids": [],
            "health_conditions": self.user_profile.get("health_conditions", []),
            "include_recommendations": True,
            "strict_mode": True
        }

    def _build_injury_risk_params(self) -> Dict[str, Any]:
        """构建损伤风险评估参数"""
        return {
            "user_id": self.user_profile.get("user_id"),
            "planned_exercises": [],
            "training_intensity": self.user_profile.get("training_intensity", "moderate"),
            "session_duration_minutes": self.user_profile.get("session_duration", 60),
            "include_prevention_plan": True,
            "risk_tolerance_level": "moderate",
            "previous_injuries": self.user_profile.get("injury_history", []),
            "current_pain_areas": self.user_profile.get("current_pain_areas", [])
        }

    def _build_movement_pattern_params(self) -> Dict[str, Any]:
        """构建动作模式平衡参数"""
        return {
            "current_program": [],
            "target_muscle_groups": self.user_profile.get("target_muscle_groups", ["chest", "back"])
        }

    def _build_tdee_params(self) -> Dict[str, Any]:
        """构建TDEE计算参数"""
        training_goal = self._get_primary_goal("hypertrophy")

        return {
            "training_frequency_per_week": self.user_profile.get("preferred_training_days", 3),
            "training_intensity": self.user_profile.get("training_intensity", "moderate"),
            "daily_activity_level": self.user_profile.get("activity_level", "moderately_active"),
            "fitness_goal": training_goal
        }

    def _build_meal_plan_params(self) -> Dict[str, Any]:
        """构建膳食计划参数"""
        training_goal = self._get_primary_goal("hypertrophy")

        dietary_prefs = self.user_profile.get("dietary_preferences", [])
        dietary_pref = dietary_prefs[0] if isinstance(dietary_prefs, list) and dietary_prefs else "balanced"

        target_calories = self.user_profile.get("target_calories", 2000)

        return {
            "target_calories": target_calories,
            "target_protein_grams": self.user_profile.get("target_protein_grams", target_calories * 0.3 / 4),
            "target_carbs_grams": self.user_profile.get("target_carbs_grams", target_calories * 0.4 / 4),
            "target_fat_grams": self.user_profile.get("target_fat_grams", target_calories * 0.3 / 9),
            "dietary_preference": dietary_pref,
            "meals_per_day": self.user_profile.get("meals_per_day", 4),
            "training_days_per_week": self.user_profile.get("preferred_training_days", 3),
            "fitness_goal": training_goal
        }

    def _build_volume_calculator_params(self) -> Dict[str, Any]:
        """构建训练量计算器参数"""
        target_muscles = self.user_profile.get("target_muscle_groups", [])
        muscle_group = target_muscles[0] if isinstance(target_muscles, list) and target_muscles else "chest"
        
        # 使用统一的目标获取方法
        training_goal = self._get_primary_goal("hypertrophy")

        recovery_value = self.user_profile.get("recovery_capacity", 0.7)
        if isinstance(recovery_value, (int, float)):
            if recovery_value < 0.4:
                recovery_capacity = "low"
            elif recovery_value < 0.7:
                recovery_capacity = "moderate"
            else:
                recovery_capacity = "high"
        else:
            recovery_capacity = recovery_value if recovery_value in ["low", "moderate", "high"] else "moderate"

        return {
            "muscle_group": muscle_group,
            "training_goal": training_goal,
            "training_frequency_per_week": self.user_profile.get("preferred_training_days", 3),
            "recovery_capacity": recovery_capacity
        }

    def _build_analytics_params(self) -> Dict[str, Any]:
        """构建分析参数"""
        return {
            "user_id": self.user_profile.get("user_id"),
            "time_period": "month",
            "focus_areas": self.user_profile.get("fitness_goals", []),
            "include_comparisons": True,
            "include_recommendations": True
        }

    def _build_safe_exercise_modifier_params(self) -> Dict[str, Any]:
        """构建安全动作修饰器参数"""
        fitness_level = self.user_profile.get("fitness_level", "beginner")
        modification_purpose = "beginner_friendly" if fitness_level == "beginner" else "injury_prevention"
        
        return {
            "user_id": self.user_profile.get("user_id"),
            "exercise_id": "",
            "modification_purpose": modification_purpose,
            "user_injuries": self.user_profile.get("injury_history", []),
            "safety_requirements": [],
            "available_equipment": self.user_profile.get("available_equipment", []),
            "modification_preference": "moderate"
        }

    def _build_exercise_alternative_params(self) -> Dict[str, Any]:
        """构建动作替代查找器参数"""
        return {
            "user_id": self.user_profile.get("user_id"),
            "original_exercise_id": "",
            "reason": "variety",
            "constraints": {
                "available_equipment": self.user_profile.get("available_equipment", []),
                "fitness_level": self.user_profile.get("fitness_level", "beginner"),
                "max_alternatives": 5
            }
        }

    def _build_nutrition_intake_params(self) -> Dict[str, Any]:
        """构建营养摄入分析器参数"""
        training_goal = self._get_primary_goal("hypertrophy")

        target_calories = self.user_profile.get("target_calories", 2000)

        return {
            "daily_food_intake": [],
            "target_calories": target_calories,
            "target_protein_grams": self.user_profile.get("target_protein_grams", target_calories * 0.3 / 4),
            "target_carbs_grams": self.user_profile.get("target_carbs_grams", target_calories * 0.4 / 4),
            "target_fat_grams": self.user_profile.get("target_fat_grams", target_calories * 0.3 / 9),
            "include_micronutrients": False,
            "fitness_goal": training_goal
        }

    def _build_exercise_nutrition_params(self) -> Dict[str, Any]:
        """构建运动营养优化器参数"""
        training_goal = self._get_primary_goal("hypertrophy")

        weight_kg = self.user_profile.get("weight_kg", 65)
        daily_protein_target = weight_kg * 1.8
        daily_carbs_target = weight_kg * 4

        return {
            "training_type": training_goal,
            "training_duration_minutes": self.user_profile.get("session_duration", 60),
            "training_intensity": self.user_profile.get("training_intensity", "moderate"),
            "training_time": "afternoon",
            "weight_kg": weight_kg,
            "fitness_goal": training_goal,
            "daily_protein_target": daily_protein_target,
            "daily_carbs_target": daily_carbs_target
        }



class TaskExecutor:
    """
    任务执行器
    
    负责执行单个DAG任务，包括参数处理、缓存、重试和MCP调用。
    """

    def __init__(
        self,
        mcp_orchestrator=None,
        cache_manager=None,
        resource_pools: Dict[str, asyncio.Semaphore] = None,
        visualizer=None,
        config_loader=None,
        parameter_extractor=None,
        parameter_converter=None,
        parameter_validator=None
    ):
        self.logger = logging.getLogger(__name__)
        self.mcp_orchestrator = mcp_orchestrator
        self.cache_manager = cache_manager
        self.resource_pools = resource_pools or {}
        self.visualizer = visualizer
        self.config_loader = config_loader
        self.parameter_extractor = parameter_extractor
        self.parameter_converter = parameter_converter
        self.parameter_validator = parameter_validator

    async def execute_task(
        self,
        task: DAGTask,
        execution_id: str,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行单个任务"""
        task.status = TaskStatus.RUNNING
        task.start_time = time.time()

        # 设置上游任务结果（用于参数提取）
        task._upstream_results = previous_results

        if self.visualizer:
            self.visualizer.log_tool_execution(
                tool_name=task.tool_name,
                status="running",
                message="开始执行"
            )

        try:
            # 增强参数
            enhanced_params = self._enhance_task_params(task, previous_results)
            task.params = enhanced_params

            # 获取资源锁
            mcp_server = task.tool_metadata.mcp_server
            if mcp_server in self.resource_pools:
                async with self.resource_pools[mcp_server]:
                    result = await self._execute_with_retry(task, previous_results)
            else:
                result = await self._execute_with_retry(task, previous_results)

            # 记录完成
            duration = time.time() - task.start_time
            if self.visualizer:
                self.visualizer.log_tool_execution(
                    tool_name=task.tool_name,
                    status="completed",
                    message="执行成功",
                    duration=duration
                )

            return result

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)

            duration = time.time() - task.start_time
            if self.visualizer:
                self.visualizer.log_tool_execution(
                    tool_name=task.tool_name,
                    status="failed",
                    message="执行失败",
                    duration=duration,
                    error=str(e)
                )

            raise

    async def _execute_with_retry(
        self,
        task: DAGTask,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """带重试的任务执行"""
        max_retries = task.tool_metadata.retry_count

        for attempt in range(max_retries + 1):
            try:
                # 检查缓存
                if task.tool_metadata.cacheable:
                    cached_result = await self._check_cache(task)
                    if cached_result:
                        task.status = TaskStatus.COMPLETED
                        task.end_time = time.time()
                        return cached_result

                # 执行任务
                result = await self._call_tool(task, previous_results)

                # 缓存结果
                if task.tool_metadata.cacheable:
                    await self._cache_result(task, result)

                task.status = TaskStatus.COMPLETED
                task.end_time = time.time()

                return result

            except Exception as e:
                if attempt < max_retries:
                    task.retry_count = attempt + 1
                    wait_time = 2 ** attempt
                    logger.warning(f"⚠️ 任务 {task.tool_name} 执行失败，{wait_time}s后重试 (第{attempt + 1}次)")
                    await asyncio.sleep(wait_time)
                else:
                    raise

        raise RuntimeError(f"任务 {task.tool_name} 达到最大重试次数")

    async def _check_cache(self, task: DAGTask) -> Optional[Dict[str, Any]]:
        """检查缓存"""
        if self.cache_manager:
            try:
                cache_key = self._generate_cache_key(task)
                cached_result = await self.cache_manager.get_cache(cache_key)
                if cached_result:
                    return cached_result
            except Exception as e:
                logger.warning(f"缓存检查失败: {task.tool_name}, {e}")
        return None

    async def _cache_result(self, task: DAGTask, result: Dict[str, Any]):
        """缓存结果"""
        if self.cache_manager and task.tool_metadata.cacheable:
            try:
                cache_key = self._generate_cache_key(task)
                await self.cache_manager.set_cache(
                    cache_key, result, ttl=task.tool_metadata.cache_ttl
                )
            except Exception as e:
                logger.warning(f"缓存存储失败: {task.tool_name}, {e}")

    def _generate_cache_key(self, task: DAGTask) -> str:
        """生成缓存键"""
        key_data = {
            "tool_name": task.tool_name,
            "params": task.params,
            "user_id": task.params.get("user_id")
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    async def _call_tool(
        self,
        task: DAGTask,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用工具"""
        tool_name = task.tool_name
        
        # 用户档案优先从context获取
        if tool_name == "get_user_profile":
            context = previous_results.get("_context", {})
            user_profile = context.get("user_profile")
            user_id = context.get("user_id")
            
            if user_profile:
                logger.info("✅ 从context获取用户档案（0延迟）")
                return {
                    "success": True,
                    "user_id": user_id,
                    "profile": user_profile,
                    "source": "context",
                    "cached": True
                }
        
        # 参数处理管道（不包含验证，验证在跳过检查之后）
        await self._process_parameters_without_validation(task, previous_results)

        # 增强任务参数（从上游结果中提取缺失参数）
        self._enhance_additional_params(task, previous_results)

        # 检查是否应该跳过（在参数验证之前）
        skip_result = self._check_skip_conditions(task)
        if skip_result:
            return skip_result

        # 参数验证（在跳过检查之后）
        await self._validate_parameters(task)
        
        # 调用MCP工具
        if self.mcp_orchestrator:
            try:
                # 获取MCP服务器名称
                mcp_server = task.tool_metadata.mcp_server
                
                mcp_result = await self.mcp_orchestrator.call_tool(
                    mcp_server=mcp_server,
                    tool_name=task.tool_name,
                    params=task.params
                )
                
                # 处理Pydantic模型：转换为字典
                if hasattr(mcp_result, 'model_dump'):
                    logger.debug(f"🔄 转换Pydantic模型为字典: {task.tool_name}")
                    mcp_result = mcp_result.model_dump()
                
                if hasattr(mcp_result, 'success'):
                    if mcp_result.success:
                        logger.info(f"✅ MCP工具调用成功: {task.tool_name}")
                        result_data = mcp_result.data or {}
                        # 确保data也是字典
                        if hasattr(result_data, 'model_dump'):
                            result_data = result_data.model_dump()
                        return result_data
                    else:
                        if hasattr(mcp_result, 'fallback_used') and mcp_result.fallback_used:
                            logger.warning(f"⚠️ MCP工具调用失败，使用降级结果: {task.tool_name}")
                            result_data = mcp_result.data or {}
                            if hasattr(result_data, 'model_dump'):
                                result_data = result_data.model_dump()
                            return result_data
                        else:
                            raise Exception(f"MCP工具调用失败: {getattr(mcp_result, 'error', 'Unknown error')}")
                elif isinstance(mcp_result, dict):
                    # 直接返回字典结果
                    if mcp_result.get("success", True):
                        logger.info(f"✅ MCP工具调用成功: {task.tool_name}")
                        return mcp_result
                    else:
                        raise Exception(f"MCP工具调用失败: {mcp_result.get('error', 'Unknown error')}")
                else:
                    # 其他类型，尝试转换为字典
                    if hasattr(mcp_result, 'model_dump'):
                        return mcp_result.model_dump()
                    return mcp_result
                    
            except Exception as e:
                logger.error(f"❌ MCP工具调用异常: {task.tool_name}, 错误: {e}")
                return {
                    "success": False,
                    "error": str(e),
                    "tool_name": task.tool_name,
                    "fallback": True,
                    "message": f"工具 {task.tool_name} 暂时不可用"
                }
        else:
            logger.warning(f"⚠️ 没有MCP编排器，使用本地实现: {task.tool_name}")
            return await self._call_local_tool(task.tool_name, task.params)

    async def _process_parameters(self, task: DAGTask, previous_results: Dict[str, Any]):
        """参数处理管道（完整版，包含验证）"""
        await self._process_parameters_without_validation(task, previous_results)
        await self._validate_parameters(task)

    async def _process_parameters_without_validation(self, task: DAGTask, previous_results: Dict[str, Any]):
        """参数处理管道（不包含验证，用于跳过检查之前）"""
        tool_name = task.tool_name
        
        # 步骤1: 参数提取
        if self.config_loader and self.parameter_extractor:
            try:
                tool_config = self.config_loader.get_tool_config(tool_name)
                if tool_config and tool_config.param_mappings:
                    from src.framework.orchestration.parameter_extractor import ParamMapping
                    
                    param_mappings = [
                        ParamMapping(
                            source_task=mapping.source_task,
                            source_path=mapping.source_path,
                            target_param=mapping.target_param,
                            converter=mapping.converter,
                            default_value=mapping.default_value
                        )
                        for mapping in tool_config.param_mappings
                    ]
                    
                    # 构建workflow_state用于ParameterExtractor的回退提取
                    # workflow_state包含context和query_analysis的数据
                    workflow_state = self._build_workflow_state(previous_results)
                    
                    # 调用参数提取器，传递workflow_state参数
                    extracted_params = self.parameter_extractor.extract_from_upstream(
                        param_mappings=param_mappings,
                        upstream_results=previous_results,
                        context={"tool_name": tool_name},
                        workflow_state=workflow_state  # 传递workflow_state启用回退提取
                    )
                    task.params.update(extracted_params)
            except Exception as e:
                logger.error(f"参数提取失败: {e}")
        
        # 步骤1.5: 确保user_id存在（跳过已由 _enhance_task_params 设置的情况）
        if not task.params.get("user_id"):
            self._ensure_user_id(task, previous_results)
        
        # 步骤2: 参数转换
        if self.parameter_converter:
            try:
                converted_params = self.parameter_converter.convert_params(
                    params=task.params, tool_schema=None, param_types=None
                )
                task.params = converted_params
            except Exception as e:
                logger.error(f"参数转换失败: {e}")

    async def _validate_parameters(self, task: DAGTask):
        """参数验证（在跳过检查之后调用）"""
        tool_name = task.tool_name
        
        # 步骤3: 参数验证
        if self.parameter_validator and self.config_loader:
            validation_result = self.parameter_validator.validate_params(
                params=task.params, tool_name=tool_name, tool_schema=None, param_schema=None
            )
            
            if not validation_result.is_valid:
                validation_config = self.config_loader.get_validation_config()
                strict_mode = validation_config.get('strict_mode', True)
                
                if strict_mode:
                    error_msg = f"参数验证失败: {tool_name}\n"
                    for error in validation_result.errors:
                        error_msg += f"  - {error}\n"
                    raise ValueError(error_msg)

    def _build_workflow_state(self, previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建workflow_state用于ParameterExtractor的回退提取
        
        从previous_results中提取context和query_analysis数据，
        构建符合ParameterExtractor.WORKFLOW_STATE_MAPPINGS格式的状态对象。
        
        Args:
            previous_results: 之前任务的执行结果
            
        Returns:
            workflow_state字典，包含user_id, query, session_id, query_analysis等
        """
        workflow_state = {}
        
        # 从_context提取基础数据
        context = previous_results.get("_context", {})
        if context:
            workflow_state["user_id"] = context.get("user_id")
            workflow_state["query"] = context.get("query")
            workflow_state["session_id"] = context.get("session_id")
            workflow_state["user_profile"] = context.get("user_profile")
        
        # 从query_analysis任务结果提取
        query_analysis = previous_results.get("query_analysis", {})
        if query_analysis:
            workflow_state["query_analysis"] = {
                "intent": query_analysis.get("intent"),
                "entities": query_analysis.get("entities", []),
                "constraints": query_analysis.get("constraints", {}),
                "complexity": query_analysis.get("complexity"),
                "confidence": query_analysis.get("confidence"),
            }
        
        return workflow_state

    def _ensure_user_id(self, task: DAGTask, previous_results: Dict[str, Any]):
        """确保user_id参数存在"""
        if "user_id" not in task.params or not task.params["user_id"]:
            if "get_user_profile" in previous_results:
                user_profile_result = previous_results["get_user_profile"]
                if isinstance(user_profile_result, dict):
                    user_id = user_profile_result.get("user_id")
                    if not user_id:
                        profile = user_profile_result.get("profile", {})
                        user_id = profile.get("user_id")
                    if user_id:
                        task.params["user_id"] = user_id
            
            if not task.params.get("user_id"):
                context = previous_results.get("_context", {})
                user_id = context.get("user_id")
                if user_id:
                    task.params["user_id"] = user_id

    def _try_extract_missing_param(self, task: DAGTask, tool_name: str, param_name: str):
        """
        尝试从上游任务结果中提取缺失的参数

        Args:
            task: 当前任务
            tool_name: 工具名称
            param_name: 参数名称
        """
        try:
            # 获取上游任务结果（需要在调用此方法之前设置）
            upstream_results = getattr(task, '_upstream_results', {})

            if not upstream_results:
                return

            # 尝试从 intelligent_exercise_selector 结果中提取
            if "intelligent_exercise_selector" in upstream_results:
                result = self._extract_actual_result(upstream_results["intelligent_exercise_selector"])

                # 提取 exercise_id
                if param_name in ["original_exercise_id", "exercise_id"]:
                    exercise_id = None

                    # 优先从 recommendations 中提取
                    recommendations = result.get("recommendations", [])
                    if recommendations and len(recommendations) > 0:
                        first_exercise = recommendations[0]
                        if hasattr(first_exercise, 'model_dump'):
                            first_exercise = first_exercise.model_dump()
                        elif hasattr(first_exercise, 'dict'):
                            first_exercise = first_exercise.dict()

                        if isinstance(first_exercise, dict):
                            exercise_id = first_exercise.get("exercise_id") or first_exercise.get("id")

                    # 如果 recommendations 为空，尝试从 selected_exercises 提取
                    if not exercise_id:
                        exercises = result.get("selected_exercises", [])
                        if exercises and len(exercises) > 0:
                            first_exercise = exercises[0]
                            if hasattr(first_exercise, 'model_dump'):
                                first_exercise = first_exercise.model_dump()
                            elif hasattr(first_exercise, 'dict'):
                                first_exercise = first_exercise.dict()

                            if isinstance(first_exercise, dict):
                                exercise_id = first_exercise.get("exercise_id") or first_exercise.get("id")

                    if exercise_id:
                        task.params[param_name] = exercise_id
                        self.logger.info(f"✅ 从intelligent_exercise_selector提取{param_name}: {exercise_id}")

        except Exception as e:
            self.logger.warning(f"⚠️ 提取缺失参数失败: {tool_name}.{param_name}, 错误: {e}")

    def _enhance_additional_params(self, task: DAGTask, previous_results: Dict[str, Any]):
        """
        增强任务参数（从上游结果中提取缺失参数）

        注意：此方法仅补充缺失参数，不覆盖已由 _enhance_task_params 设置的参数。

        Args:
            task: 当前任务
            previous_results: 上游任务结果
        """
        tool_name = task.tool_name

        # 设置上游结果（用于 _try_extract_missing_param 方法）
        task._upstream_results = previous_results

        # 为需要 exercise_id 的工具提取参数（仅在缺失时）
        if tool_name in ["exercise_alternative_finder", "safe_exercise_modifier", "intelligent_weight_calculator"]:
            param_name = "original_exercise_id" if tool_name == "exercise_alternative_finder" else "exercise_id"

            if not task.params.get(param_name):
                self._try_extract_missing_param(task, tool_name, param_name)

    def _check_skip_conditions(self, task: DAGTask) -> Optional[Dict[str, Any]]:
        """检查是否应该跳过任务"""
        tool_name = task.tool_name

        skip_configs = {
            "exercise_alternative_finder": ("original_exercise_id", "缺少必需参数 original_exercise_id"),
            "safe_exercise_modifier": ("exercise_id", "缺少必需参数 exercise_id"),
            "intelligent_weight_calculator": ("exercise_id", "缺少必需参数 exercise_id"),
        }

        if tool_name in skip_configs:
            param_name, reason = skip_configs[tool_name]
            param_value = task.params.get(param_name)
            if not param_value or param_value == "":
                logger.warning(f"⚠️ 跳过 {tool_name}：{reason}")
                return {
                    "success": False,
                    "skipped": True,
                    "tool_name": tool_name,
                    "reason": reason,
                    "message": f"{tool_name} 已跳过"
                }

        if tool_name == "movement_pattern_balancer":
            current_program = task.params.get("current_program", [])
            if not current_program or len(current_program) == 0:
                logger.warning(f"⚠️ 跳过 {tool_name}：current_program 为空")
                return {
                    "success": False,
                    "skipped": True,
                    "tool_name": tool_name,
                    "reason": "缺少必需参数 current_program",
                    "message": f"{tool_name} 已跳过"
                }

        return None

    def _enhance_task_params(
        self,
        task: DAGTask,
        previous_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """增强任务参数"""
        enhanced_params = task.params.copy()
        tool_name = task.tool_name
        
        # 处理user_id
        self._ensure_user_id_in_params(enhanced_params, previous_results)

        # 处理user_profile（从get_user_profile结果补充）
        self._ensure_user_profile_in_params(enhanced_params, previous_results)

        # 处理exercises参数
        if tool_name in ["injury_risk_assessor", "muscle_group_volume_calculator", "movement_pattern_balancer"]:
            self._enhance_exercises_param(enhanced_params, previous_results)
        
        # 处理contraindications_checker的exercise_ids
        if tool_name == "contraindications_checker":
            self._enhance_exercise_ids_param(enhanced_params, previous_results)
        
        # 处理exercise_id参数
        if tool_name in ["exercise_alternative_finder", "intelligent_weight_calculator", "safe_exercise_modifier"]:
            self._enhance_exercise_id_param(enhanced_params, previous_results, tool_name)
        
        return enhanced_params

    def _ensure_user_id_in_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]):
        """确保params中有user_id"""
        if "user_id" not in params or not params["user_id"]:
            if "get_user_profile" in previous_results:
                result = previous_results["get_user_profile"]
                if isinstance(result, dict):
                    profile = result.get("profile", {})
                    user_id = profile.get("user_id") or result.get("user_id")
                    if user_id:
                        params["user_id"] = user_id
            
            if not params.get("user_id"):
                context = previous_results.get("_context", {})
                user_id = context.get("user_id")
                if user_id:
                    params["user_id"] = user_id

    def _ensure_user_profile_in_params(self, params: Dict[str, Any], previous_results: Dict[str, Any]):
        """确保params中有user_profile（从get_user_profile结果补充）"""
        if not params.get("user_profile"):
            if "get_user_profile" in previous_results:
                result = previous_results["get_user_profile"]
                if isinstance(result, dict):
                    profile = result.get("profile", {})
                    if profile:
                        params["user_profile"] = profile

            if not params.get("user_profile"):
                context = previous_results.get("_context", {})
                user_profile = context.get("user_profile")
                if user_profile:
                    params["user_profile"] = user_profile

    def _enhance_exercises_param(self, params: Dict[str, Any], previous_results: Dict[str, Any]):
        """增强exercises参数"""
        if "exercises" not in params or not params["exercises"]:
            exercises = []
            
            if "intelligent_exercise_selector" in previous_results:
                result = self._extract_actual_result(previous_results["intelligent_exercise_selector"])
                exercises = result.get("selected_exercises", []) or result.get("exercises", []) or result.get("recommendations", [])
            
            if not exercises and "semantic_search" in previous_results:
                result = self._extract_actual_result(previous_results["semantic_search"])
                exercises = result.get("results", [])
            
            params["exercises"] = exercises

    def _enhance_exercise_ids_param(self, params: Dict[str, Any], previous_results: Dict[str, Any]):
        """增强exercise_ids参数"""
        if "exercise_ids" not in params or not params["exercise_ids"]:
            exercise_ids = []
            
            if "intelligent_exercise_selector" in previous_results:
                result = self._extract_actual_result(previous_results["intelligent_exercise_selector"])
                recommendations = result.get("recommendations", [])
                if recommendations:
                    exercise_ids = [
                        ex.get("exercise_id") or ex.get("id")
                        for ex in recommendations
                        if isinstance(ex, dict) and (ex.get("exercise_id") or ex.get("id"))
                    ]
            
            params["exercise_ids"] = exercise_ids

    def _enhance_exercise_id_param(self, params: Dict[str, Any], previous_results: Dict[str, Any], tool_name: str):
        """增强exercise_id参数"""
        param_name = "original_exercise_id" if tool_name == "exercise_alternative_finder" else "exercise_id"
        
        if param_name not in params or not params.get(param_name):
            exercise_id = None
            
            if "intelligent_exercise_selector" in previous_results:
                result = self._extract_actual_result(previous_results["intelligent_exercise_selector"])
                
                # 优先从recommendations中提取
                recommendations = result.get("recommendations", [])
                
                if recommendations and len(recommendations) > 0:
                    first_exercise = recommendations[0]
                    
                    # 调试：检查first_exercise的类型
                    self.logger.debug(f"🔍 first_exercise类型: {type(first_exercise)}")
                    self.logger.debug(f"🔍 first_exercise内容: {first_exercise}")
                    
                    # 如果是Pydantic模型，转换为字典
                    if hasattr(first_exercise, 'model_dump'):
                        self.logger.debug(f"🔄 转换Pydantic模型为字典")
                        first_exercise = first_exercise.model_dump()
                    elif hasattr(first_exercise, 'dict'):
                        self.logger.debug(f"🔄 转换Pydantic模型为字典（旧版）")
                        first_exercise = first_exercise.dict()
                    
                    if isinstance(first_exercise, dict):
                        exercise_id = first_exercise.get("exercise_id") or first_exercise.get("id")
                        self.logger.info(f"✅ 从recommendations[0]提取exercise_id: {exercise_id}")
                
                # 如果recommendations为空，尝试从selected_exercises提取
                if not exercise_id:
                    exercises = result.get("selected_exercises", [])
                    if exercises and len(exercises) > 0:
                        first_exercise = exercises[0]
                        
                        # 如果是Pydantic模型，转换为字典
                        if hasattr(first_exercise, 'model_dump'):
                            first_exercise = first_exercise.model_dump()
                        elif hasattr(first_exercise, 'dict'):
                            first_exercise = first_exercise.dict()
                        
                        if isinstance(first_exercise, dict):
                            exercise_id = first_exercise.get("exercise_id") or first_exercise.get("id")
                            self.logger.info(f"✅ 从selected_exercises[0]提取exercise_id: {exercise_id}")
                
                # 如果还是没有，记录详细的调试信息
                if not exercise_id:
                    self.logger.warning(
                        f"⚠️ 无法从intelligent_exercise_selector提取exercise_id\n"
                        f"  - recommendations数量: {len(recommendations)}\n"
                        f"  - selected_exercises数量: {len(result.get('selected_exercises', []))}\n"
                        f"  - result keys: {list(result.keys())}"
                    )
            else:
                self.logger.warning(f"⚠️ previous_results中没有intelligent_exercise_selector")
            
            params[param_name] = exercise_id or ""
            
            if not exercise_id:
                self.logger.error(
                    f"❌ {tool_name}的{param_name}参数为空\n"
                    f"  - previous_results keys: {list(previous_results.keys())}"
                )

    def _extract_actual_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """从工具结果中提取实际数据"""
        if not isinstance(result, dict):
            return result
        
        if "data" in result:
            actual_result = result.get("data", result)
            if isinstance(actual_result, dict) and "data" in actual_result:
                actual_result = actual_result.get("data", actual_result)
            return actual_result
        
        return result

    async def _call_local_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """本地工具调用"""
        return {
            "tool": tool_name,
            "status": "success",
            "data": params,
            "timestamp": time.time()
        }
