# -*- coding: utf-8 -*-
"""
DAG编排器 - 核心编排逻辑

基于DAG模板系统，执行预定义的工作流程。
支持三段式架构：LLM选择 → 程序执行 → LLM综合

核心特性：
1. 基于模板的执行图构建
2. 智能依赖解析和拓扑排序
3. 并行执行优化
4. 错误处理和容错机制
5. 性能监控和统计

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-28
"""

import asyncio
import logging
import time
import uuid
from typing import Dict, List, Optional, Any
from collections import defaultdict

from .models import (
    TaskStatus,
    TaskPriority,
    ToolMetadata,
    DAGTask,
    ExecutionLevel,
    DAGExecutionResult,
)
from ..dag_template_system import DAGTemplate, DAGTemplateManager

logger = logging.getLogger(__name__)


class EnhancedDAGOrchestrator:
    """
    增强版DAG编排器 v3.0 - 基于模板执行
    
    职责：
    1. 管理DAG模板和工具元数据
    2. 构建和执行DAG任务
    3. 处理依赖关系和并行执行
    4. 记录性能统计和执行历史
    """

    def __init__(
        self,
        mcp_orchestrator=None,
        cache_manager=None,
        template_manager: DAGTemplateManager = None,
        visualizer=None  # DAGVisualizer已删除，保留参数以兼容
    ):
        """
        初始化DAG编排器
        
        Args:
            mcp_orchestrator: MCP工具管理器
            cache_manager: 缓存管理器
            template_manager: DAG模板管理器
            visualizer: DAG可视化器（已废弃）
        """
        self.mcp_orchestrator = mcp_orchestrator
        self.cache_manager = cache_manager
        self.template_manager = template_manager or DAGTemplateManager()
        self.visualizer = visualizer  # DAGVisualizer已删除，visualizer为None时不使用可视化
        
        # 初始化工具元数据和依赖图
        self.tool_metadata_registry = self._initialize_tool_metadata()
        self.dependency_graph = self._build_dependency_graph()
        self.resource_pools = self._initialize_resource_pools()
        
        # 执行历史和性能统计
        self.execution_history = []
        self.performance_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "average_execution_time": 0.0,
            "cache_hit_rate": 0.0,
            "template_usage": defaultdict(int)
        }
        
        # 初始化参数处理层组件
        self._init_parameter_processors()
        
        logger.info(f"✅ DAG编排器初始化完成，加载了 {len(self.template_manager.get_all_templates())} 个模板")

    def _init_parameter_processors(self):
        """初始化参数处理层组件"""
        from src.framework.orchestration.config_loader import get_config_loader
        from src.framework.orchestration.parameter_extractor import ParameterExtractor
        from src.framework.orchestration.parameter_converter import ParameterConverter
        from src.framework.orchestration.parameter_validator import ParameterValidator
        
        self.config_loader = get_config_loader()
        self.parameter_extractor = ParameterExtractor()
        self.parameter_converter = ParameterConverter()
        self.parameter_validator = ParameterValidator()
        
        logger.info("✅ 参数处理层初始化完成（使用ParameterExtractor + ParameterValidator）")

    def _initialize_tool_metadata(self) -> Dict[str, ToolMetadata]:
        """初始化工具元数据注册表"""
        return {
            # 基础数据工具
            "get_user_profile": ToolMetadata(
                name="get_user_profile",
                mcp_server="user-profile-stdio",
                execution_time=0.5,
                cacheable=True,
                cache_ttl=3600,
                parallel_safe=True,
                supports_concurrent=True,
                priority=TaskPriority.CRITICAL,
                retry_count=2
            ),
            "tdee_calculator": ToolMetadata(
                name="tdee_calculator",
                mcp_server="python_builtin",
                execution_time=1.0,
                cacheable=True,
                cache_ttl=1800,
                parallel_safe=True,
                supports_concurrent=True,
                priority=TaskPriority.HIGH
            ),
            "chinese_food_analyzer": ToolMetadata(
                name="chinese_food_analyzer",
                mcp_server="python_builtin",
                execution_time=1.5,
                cacheable=True,
                cache_ttl=7200,
                parallel_safe=True,
                priority=TaskPriority.NORMAL
            ),
            "weight_calculator": ToolMetadata(
                name="weight_calculator",
                mcp_server="python_builtin",
                execution_time=0.8,
                cacheable=True,
                cache_ttl=3600,
                parallel_safe=True,
                priority=TaskPriority.NORMAL
            ),
            "rpe_recommender": ToolMetadata(
                name="rpe_recommender",
                mcp_server="python_builtin",
                execution_time=0.5,
                cacheable=True,
                cache_ttl=1800,
                parallel_safe=True,
                priority=TaskPriority.NORMAL
            ),
            # 安全工具 (高优先级，不可并行)
            "contraindications_checker": ToolMetadata(
                name="contraindications_checker",
                mcp_server="python_builtin",
                execution_time=2.0,
                cacheable=False,
                parallel_safe=False,
                priority=TaskPriority.CRITICAL,
                timeout=15.0
            ),
            "injury_risk_assessor": ToolMetadata(
                name="injury_risk_assessor",
                mcp_server="python_builtin",
                execution_time=1.8,
                cacheable=False,
                parallel_safe=False,
                priority=TaskPriority.CRITICAL,
                timeout=15.0
            ),
            "advanced_safety_monitor": ToolMetadata(
                name="advanced_safety_monitor",
                mcp_server="python_builtin",
                execution_time=1.5,
                cacheable=False,
                parallel_safe=False,
                priority=TaskPriority.CRITICAL,
                timeout=10.0
            ),
            # 动作工具
            "intelligent_exercise_selector": ToolMetadata(
                name="intelligent_exercise_selector",
                mcp_server="python_builtin",
                execution_time=3.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=["contraindications_checker", "injury_risk_assessor"],
                priority=TaskPriority.HIGH,
                timeout=20.0
            ),
            "exercise_alternative_finder": ToolMetadata(
                name="exercise_alternative_finder",
                mcp_server="python_builtin",
                execution_time=2.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=["intelligent_exercise_selector"],
                priority=TaskPriority.NORMAL,
                timeout=15.0
            ),
            "safe_exercise_modifier": ToolMetadata(
                name="safe_exercise_modifier",
                mcp_server="python_builtin",
                execution_time=2.5,
                cacheable=False,
                parallel_safe=False,
                dependencies=["injury_risk_assessor"],
                priority=TaskPriority.HIGH,
                timeout=15.0
            ),
            "movement_pattern_balancer": ToolMetadata(
                name="movement_pattern_balancer",
                mcp_server="python_builtin",
                execution_time=2.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=["get_user_profile"],
                priority=TaskPriority.NORMAL,
                timeout=15.0
            ),
            # 训练规划工具
            "professional_program_designer": ToolMetadata(
                name="professional_program_designer",
                mcp_server="python_builtin",
                execution_time=8.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=[
                    "intelligent_exercise_selector",
                    "muscle_group_volume_calculator",
                    "movement_pattern_balancer"
                ],
                priority=TaskPriority.CRITICAL,
                timeout=30.0
            ),
            "periodized_program_designer": ToolMetadata(
                name="periodized_program_designer",
                mcp_server="python_builtin",
                execution_time=6.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=[
                    "assess_strength_level",
                    "muscle_group_volume_calculator"
                ],
                priority=TaskPriority.HIGH,
                timeout=25.0
            ),
            "training_split_designer": ToolMetadata(
                name="training_split_designer",
                mcp_server="python_builtin",
                execution_time=4.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=["professional_program_designer"],
                priority=TaskPriority.HIGH,
                timeout=20.0
            ),
            "muscle_group_volume_calculator": ToolMetadata(
                name="muscle_group_volume_calculator",
                mcp_server="python_builtin",
                execution_time=2.5,
                cacheable=False,
                parallel_safe=False,
                dependencies=["get_user_profile"],
                priority=TaskPriority.HIGH,
                timeout=15.0
            ),
            "intelligent_weight_calculator": ToolMetadata(
                name="intelligent_weight_calculator",
                mcp_server="python_builtin",
                execution_time=1.5,
                cacheable=False,
                parallel_safe=False,
                dependencies=["intelligent_exercise_selector"],
                priority=TaskPriority.NORMAL,
                timeout=10.0
            ),
            # 营养工具
            "nutrition_intake_analyzer": ToolMetadata(
                name="nutrition_intake_analyzer",
                mcp_server="python_builtin",
                execution_time=2.0,
                cacheable=True,
                cache_ttl=1800,
                parallel_safe=True,
                dependencies=["tdee_calculator"],
                priority=TaskPriority.NORMAL,
                timeout=15.0
            ),
            "exercise_nutrition_optimization": ToolMetadata(
                name="exercise_nutrition_optimization",
                mcp_server="python_builtin",
                execution_time=3.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=[
                    "professional_program_designer",
                    "nutrition_intake_analyzer"
                ],
                priority=TaskPriority.HIGH,
                timeout=20.0
            ),
            "muscle_recovery_nutrition": ToolMetadata(
                name="muscle_recovery_nutrition",
                mcp_server="python_builtin",
                execution_time=2.5,
                cacheable=False,
                parallel_safe=False,
                dependencies=["exercise_nutrition_optimization"],
                priority=TaskPriority.NORMAL,
                timeout=15.0
            ),
            "nutrition_timing": ToolMetadata(
                name="nutrition_timing",
                mcp_server="python_builtin",
                execution_time=2.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=["professional_program_designer"],
                priority=TaskPriority.NORMAL,
                timeout=15.0
            ),
            "meal_plan_designer": ToolMetadata(
                name="meal_plan_designer",
                mcp_server="python_builtin",
                execution_time=6.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=[
                    "tdee_calculator",
                    "chinese_food_analyzer",
                    "professional_program_designer"
                ],
                priority=TaskPriority.HIGH,
                timeout=25.0
            ),
            # 分析工具
            "training_analytics_dashboard": ToolMetadata(
                name="training_analytics_dashboard",
                mcp_server="python_builtin",
                execution_time=4.0,
                cacheable=False,
                parallel_safe=False,
                dependencies=["professional_program_designer"],
                priority=TaskPriority.NORMAL,
                timeout=20.0
            ),
            "evidence_based_recommender": ToolMetadata(
                name="evidence_based_recommender",
                mcp_server="python_builtin",
                execution_time=2.5,
                cacheable=True,
                cache_ttl=3600,
                parallel_safe=True,
                priority=TaskPriority.NORMAL,
                timeout=15.0
            ),
            # 辅助工具
            "assess_strength_level": ToolMetadata(
                name="assess_strength_level",
                mcp_server="python_builtin",
                execution_time=1.5,
                cacheable=True,
                cache_ttl=7200,
                parallel_safe=True,
                dependencies=["get_user_profile"],
                priority=TaskPriority.HIGH
            )
        }

    def _build_dependency_graph(self) -> Dict[str, List[str]]:
        """构建工具依赖图"""
        dependencies = {}
        for tool_name, metadata in self.tool_metadata_registry.items():
            dependencies[tool_name] = metadata.dependencies.copy()
        return dependencies

    def _initialize_resource_pools(self) -> Dict[str, asyncio.Semaphore]:
        """初始化资源池"""
        return {
            "user-profile-mcp": asyncio.Semaphore(3),
            "python_builtin": asyncio.Semaphore(5),
            "graphrag-mcp": asyncio.Semaphore(2),
        }

    def _generate_execution_id(self) -> str:
        """生成执行ID"""
        return f"dag_{int(time.time())}_{uuid.uuid4().hex[:8]}"

    # ========================================================================
    # 模板执行方法
    # ========================================================================

    async def execute_template(
        self,
        template_id: str,
        user_profile: Dict[str, Any],
        session_context: Dict[str, Any] = None,
        cached_results: Dict[str, Any] = None
    ) -> DAGExecutionResult:
        """
        基于模板执行DAG
        
        Args:
            template_id: DAG模板ID
            user_profile: 用户档案
            session_context: 会话上下文
            cached_results: 缓存结果
            
        Returns:
            DAGExecutionResult: 执行结果
        """
        execution_id = self._generate_execution_id()
        start_time = time.time()

        logger.info(f"🚀 开始基于模板的DAG执行: {execution_id}")
        logger.info(f"📋 模板ID: {template_id}")

        self.performance_stats["total_executions"] += 1
        self.performance_stats["template_usage"][template_id] += 1

        try:
            # 步骤1: 加载DAG模板
            template = self.template_manager.get_template(template_id)
            if not template:
                raise ValueError(f"模板不存在: {template_id}")
            
            logger.info(f"📋 加载模板: {template.name}")
            logger.info(f"🔧 必需工具: {len(template.required_tools)}个")
            logger.info(f"⚙️ 可选工具: {len(template.optional_tools)}个")

            # 步骤2: 从模板构建DAG任务
            dag_tasks = await self._build_dag_tasks_from_template(
                template, user_profile, session_context
            )

            # 步骤3: 使用模板的依赖关系
            dependency_analysis = template.tool_dependencies

            # 步骤4: 拓扑排序
            execution_levels = self._topological_sort_from_template(
                dag_tasks, dependency_analysis, template.parallel_groups
            )

            # 步骤5: 并行优化
            optimized_levels = self._optimize_parallel_execution(
                execution_levels, cached_results
            )

            # 步骤6: 执行DAG
            execution_result = await self._execute_dag_levels(
                execution_id,
                optimized_levels,
                {"intent": template.name, "template_id": template_id},
                cached_results,
                session_context
            )

            # 更新性能统计
            self._update_performance_stats(execution_id, template_id, template.name, start_time, True)

            logger.info(f"✅ 模板执行成功: {execution_id}, 耗时: {time.time() - start_time:.2f}s")
            return execution_result

        except Exception as e:
            self.performance_stats["failed_executions"] += 1
            logger.error(f"❌ 模板执行失败: {execution_id}, 错误: {e}", exc_info=True)

            return DAGExecutionResult(
                execution_id=execution_id,
                intent_pattern=template_id,
                success=False,
                total_time=time.time() - start_time,
                levels_executed=0,
                tasks_completed=0,
                tasks_failed=1,
                errors={"execution": str(e)}
            )

    async def build_and_execute_dag(
        self,
        intent_result: Dict[str, Any],
        user_profile: Dict[str, Any],
        session_context: Dict[str, Any] = None,
        cached_results: Dict[str, Any] = None
    ) -> DAGExecutionResult:
        """
        构建并执行DAG（兼容旧接口）
        
        Args:
            intent_result: 意图识别结果
            user_profile: 用户档案
            session_context: 会话上下文
            cached_results: 缓存结果
            
        Returns:
            DAGExecutionResult: 执行结果
        """
        execution_id = self._generate_execution_id()
        start_time = time.time()

        logger.info(f"🚀 开始DAG编排执行: {execution_id}")
        logger.info(f"🎯 意图: {intent_result['intent']}")

        self.performance_stats["total_executions"] += 1

        try:
            # 步骤1: 构建DAG任务
            dag_tasks = await self._build_dag_tasks(
                intent_result, user_profile, session_context
            )

            # 步骤2: 分析依赖关系
            dependency_analysis = self._analyze_dependencies(dag_tasks)

            # 步骤3: 拓扑排序
            execution_levels = self._topological_sort(dag_tasks, dependency_analysis)

            # 步骤4: 并行优化
            optimized_levels = self._optimize_parallel_execution(
                execution_levels, cached_results
            )

            # 步骤5: 执行DAG
            execution_result = await self._execute_dag_levels(
                execution_id,
                optimized_levels,
                intent_result,
                cached_results
            )

            # 更新性能统计
            self._update_performance_stats(
                execution_id, None, intent_result["intent"], start_time, True
            )

            logger.info(f"✅ DAG执行成功: {execution_id}, 耗时: {time.time() - start_time:.2f}s")
            return execution_result

        except Exception as e:
            self.performance_stats["failed_executions"] += 1
            logger.error(f"❌ DAG执行失败: {execution_id}, 错误: {e}", exc_info=True)

            return DAGExecutionResult(
                execution_id=execution_id,
                intent_pattern=intent_result["intent"],
                success=False,
                total_time=time.time() - start_time,
                levels_executed=0,
                tasks_completed=0,
                tasks_failed=1,
                errors={"execution": str(e)}
            )

    def _update_performance_stats(
        self,
        execution_id: str,
        template_id: Optional[str],
        intent_name: str,
        start_time: float,
        success: bool
    ):
        """更新性能统计"""
        execution_time = time.time() - start_time
        
        if success:
            self.performance_stats["successful_executions"] += 1
            n = self.performance_stats["successful_executions"]
            avg = self.performance_stats["average_execution_time"]
            self.performance_stats["average_execution_time"] = (avg * (n - 1) + execution_time) / n

        self.execution_history.append({
            "execution_id": execution_id,
            "timestamp": start_time,
            "template_id": template_id,
            "intent": intent_name,
            "execution_time": execution_time,
            "success": success
        })


    # ========================================================================
    # DAG任务构建方法
    # ========================================================================

    async def _build_dag_tasks_from_template(
        self,
        template: DAGTemplate,
        user_profile: Dict[str, Any],
        session_context: Dict[str, Any] = None
    ) -> List[DAGTask]:
        """从模板构建DAG任务列表"""
        from .task_executor import TaskParamBuilder
        
        tasks = []
        param_builder = TaskParamBuilder(user_profile, session_context)

        # 添加必需工具
        for tool_name in template.required_tools:
            registry_tool_name = tool_name.replace('-', '_')
            
            if registry_tool_name in self.tool_metadata_registry:
                metadata = self.tool_metadata_registry[registry_tool_name]
                params = param_builder.build_params(registry_tool_name)

                task = DAGTask(
                    tool_name=registry_tool_name,
                    tool_metadata=metadata,
                    params=params,
                    dependencies=[dep.replace('-', '_') for dep in template.tool_dependencies.get(tool_name, [])],
                    priority=metadata.priority
                )
                tasks.append(task)
            else:
                logger.warning(f"⚠️ 工具 {tool_name} 不在注册表中，跳过")

        # 选择可选工具
        selected_optional_tools = self._select_optional_tools_from_template(
            template, user_profile
        )

        for tool_name in selected_optional_tools:
            registry_tool_name = tool_name.replace('-', '_')
            
            if registry_tool_name in self.tool_metadata_registry:
                metadata = self.tool_metadata_registry[registry_tool_name]
                params = param_builder.build_params(registry_tool_name)

                task = DAGTask(
                    tool_name=registry_tool_name,
                    tool_metadata=metadata,
                    params=params,
                    dependencies=[dep.replace('-', '_') for dep in template.tool_dependencies.get(tool_name, [])],
                    priority=TaskPriority.LOW
                )
                tasks.append(task)

        # 分配执行顺序
        for i, task in enumerate(tasks):
            task.execution_order = i

        logger.info(f"📦 从模板构建了 {len(tasks)} 个任务")
        return tasks

    async def _build_dag_tasks(
        self,
        intent_result: Dict[str, Any],
        user_profile: Dict[str, Any],
        session_context: Dict[str, Any] = None
    ) -> List[DAGTask]:
        """构建DAG任务列表（兼容旧接口）"""
        from .task_executor import TaskParamBuilder
        
        tasks = []
        param_builder = TaskParamBuilder(user_profile, session_context)

        # 添加必需工具
        for tool_name in intent_result["required_tools"]:
            if tool_name in self.tool_metadata_registry:
                metadata = self.tool_metadata_registry[tool_name]
                params = param_builder.build_params(tool_name)

                task = DAGTask(
                    tool_name=tool_name,
                    tool_metadata=metadata,
                    params=params,
                    dependencies=metadata.dependencies.copy(),
                    priority=metadata.priority
                )
                tasks.append(task)

        # 添加可选工具
        optional_tools = self._select_optional_tools(
            intent_result["optional_tools"],
            user_profile,
            intent_result["confidence"]
        )

        for tool_name in optional_tools:
            if tool_name in self.tool_metadata_registry:
                metadata = self.tool_metadata_registry[tool_name]
                params = param_builder.build_params(tool_name)

                task = DAGTask(
                    tool_name=tool_name,
                    tool_metadata=metadata,
                    params=params,
                    dependencies=metadata.dependencies.copy(),
                    priority=TaskPriority.LOW
                )
                tasks.append(task)

        # 分配执行顺序
        for i, task in enumerate(tasks):
            task.execution_order = i

        return tasks

    def _select_optional_tools_from_template(
        self,
        template: DAGTemplate,
        user_profile: Dict[str, Any]
    ) -> List[str]:
        """从模板中选择可选工具"""
        selected_tools = []
        
        # 根据模板复杂度决定选择多少可选工具
        if template.complexity_level == 3:
            selected_tools = template.optional_tools.copy()
        elif template.complexity_level == 2:
            selected_tools = template.optional_tools[:len(template.optional_tools)//2 + 1]
        else:
            selected_tools = template.optional_tools[:2]
        
        # 根据用户档案特征调整
        fitness_level = user_profile.get("fitness_level", "beginner")
        fitness_goals = user_profile.get("fitness_goals", [])
        
        if fitness_level == "beginner":
            if "safe_exercise_modifier" in template.optional_tools and "safe_exercise_modifier" not in selected_tools:
                selected_tools.append("safe_exercise_modifier")
        
        if "增肌" in fitness_goals or "muscle_gain" in fitness_goals:
            if "exercise_nutrition_optimization" in template.optional_tools and "exercise_nutrition_optimization" not in selected_tools:
                selected_tools.append("exercise_nutrition_optimization")
        
        logger.info(f"🎯 从 {len(template.optional_tools)} 个可选工具中选择了 {len(selected_tools)} 个")
        return selected_tools

    def _select_optional_tools(
        self,
        optional_tools: List[str],
        user_profile: Dict[str, Any],
        confidence: float
    ) -> List[str]:
        """选择可选工具"""
        selected_tools = []

        if confidence > 0.8:
            selected_tools.extend(optional_tools[:3])
        elif confidence > 0.6:
            selected_tools.extend(optional_tools[:2])
        elif confidence > 0.4:
            selected_tools.extend(optional_tools[:1])

        if user_profile.get("fitness_level") == "beginner":
            if "safe_exercise_modifier" in optional_tools:
                selected_tools.append("safe_exercise_modifier")

        if "增肌" in user_profile.get("fitness_goals", []):
            if "exercise_nutrition_optimization" in optional_tools:
                selected_tools.append("exercise_nutrition_optimization")

        return list(set(selected_tools))

    # ========================================================================
    # 拓扑排序和并行优化
    # ========================================================================

    def _analyze_dependencies(self, tasks: List[DAGTask]) -> Dict[str, List[str]]:
        """分析任务依赖关系"""
        dependency_map = {}
        task_names = {task.tool_name for task in tasks}

        for task in tasks:
            valid_dependencies = [dep for dep in task.dependencies if dep in task_names]
            dependency_map[task.tool_name] = valid_dependencies

        return dependency_map

    def _topological_sort_from_template(
        self,
        tasks: List[DAGTask],
        dependencies: Dict[str, List[str]],
        parallel_groups: List[List[str]]
    ) -> List[ExecutionLevel]:
        """基于模板的拓扑排序"""
        if parallel_groups:
            return self._build_levels_from_parallel_groups(tasks, parallel_groups)
        return self._topological_sort(tasks, dependencies)

    def _build_levels_from_parallel_groups(
        self,
        tasks: List[DAGTask],
        parallel_groups: List[List[str]]
    ) -> List[ExecutionLevel]:
        """从模板的并行组构建执行层级"""
        levels = []
        task_map = {task.tool_name: task for task in tasks}
        
        for level_num, group in enumerate(parallel_groups):
            level_tasks = []
            
            for tool_name in group:
                registry_tool_name = tool_name.replace('-', '_')
                if registry_tool_name in task_map:
                    task = task_map[registry_tool_name]
                    task.level = level_num
                    level_tasks.append(task)
            
            if level_tasks:
                level = ExecutionLevel(
                    level=level_num,
                    tasks=level_tasks,
                    estimated_duration=max(task.tool_metadata.execution_time for task in level_tasks),
                    can_parallel=all(task.tool_metadata.parallel_safe for task in level_tasks)
                )
                levels.append(level)
        
        logger.info(f"📊 从模板并行组构建了 {len(levels)} 个执行层级")
        return levels

    def _topological_sort(
        self,
        tasks: List[DAGTask],
        dependencies: Dict[str, List[str]]
    ) -> List[ExecutionLevel]:
        """拓扑排序 - Kahn算法"""
        in_degree = {task.tool_name: 0 for task in tasks}
        for task in tasks:
            for dep in dependencies.get(task.tool_name, []):
                in_degree[task.tool_name] += 1

        levels = []
        remaining_tasks = {task.tool_name: task for task in tasks}

        level_num = 0
        while remaining_tasks:
            current_level_tasks = []
            for task_name, task in remaining_tasks.items():
                if in_degree[task_name] == 0:
                    current_level_tasks.append(task)

            if not current_level_tasks:
                current_level_tasks = [list(remaining_tasks.values())[0]]
                logger.warning(f"⚠️ 检测到循环依赖，选择任务继续: {current_level_tasks[0].tool_name}")

            current_level_tasks.sort(key=lambda t: t.priority.value)

            level = ExecutionLevel(
                level=level_num,
                tasks=current_level_tasks,
                estimated_duration=max(task.tool_metadata.execution_time for task in current_level_tasks),
                can_parallel=all(task.tool_metadata.parallel_safe for task in current_level_tasks)
            )

            levels.append(level)

            for task in current_level_tasks:
                remaining_tasks.pop(task.tool_name)
                task.level = level_num

                for other_task in remaining_tasks.values():
                    if task.tool_name in dependencies.get(other_task.tool_name, []):
                        in_degree[other_task.tool_name] -= 1

            level_num += 1

        return levels

    def _optimize_parallel_execution(
        self,
        levels: List[ExecutionLevel],
        cached_results: Dict[str, Any] = None
    ) -> List[ExecutionLevel]:
        """并行执行优化"""
        optimized_levels = []

        for level in levels:
            if not level.can_parallel:
                optimized_levels.append(level)
                continue

            parallel_groups = self._group_parallel_safe_tasks(level.tasks, cached_results)
            level.parallel_groups = parallel_groups
            optimized_levels.append(level)

        return optimized_levels

    def _group_parallel_safe_tasks(
        self,
        tasks: List[DAGTask],
        cached_results: Dict[str, Any] = None
    ) -> List[List[DAGTask]]:
        """分组并行安全的任务"""
        groups = []
        used_tasks = set()

        cached_tasks = [task for task in tasks if task.tool_name in (cached_results or {})]
        if cached_tasks:
            groups.append(cached_tasks)
            used_tasks.update(task.tool_name for task in cached_tasks)

        mcp_groups = defaultdict(list)
        for task in tasks:
            if task.tool_name not in used_tasks:
                mcp_groups[task.tool_metadata.mcp_server].append(task)

        for mcp_server, server_tasks in mcp_groups.items():
            if len(server_tasks) == 1:
                groups.append(server_tasks)
            else:
                semaphore = self.resource_pools.get(mcp_server)
                if semaphore:
                    max_concurrent = semaphore._value
                    for i in range(0, len(server_tasks), max_concurrent):
                        group = server_tasks[i:i + max_concurrent]
                        groups.append(group)
                else:
                    groups.append(server_tasks)

        return groups


    # ========================================================================
    # DAG执行方法
    # ========================================================================

    async def _execute_dag_levels(
        self,
        execution_id: str,
        levels: List[ExecutionLevel],
        intent_result: Dict[str, Any],
        cached_results: Dict[str, Any] = None,
        session_context: Dict[str, Any] = None
    ) -> DAGExecutionResult:
        """执行DAG层级"""
        from .task_executor import TaskExecutor
        
        start_time = time.time()
        all_results = (cached_results or {}).copy()
        
        # 将session_context中的_context合并到all_results
        if session_context and "_context" in session_context:
            all_results["_context"] = session_context["_context"]
            logger.info("✅ 已将context传递到DAG执行环境")
        else:
            logger.warning(f"⚠️ session_context中没有_context")
        
        all_errors = {}
        tasks_completed = 0
        tasks_failed = 0
        tasks_skipped = 0

        logger.info(f"📊 执行DAG: {len(levels)}个层级")

        # 创建任务执行器
        task_executor = TaskExecutor(
            mcp_orchestrator=self.mcp_orchestrator,
            cache_manager=self.cache_manager,
            resource_pools=self.resource_pools,
            visualizer=self.visualizer,
            config_loader=self.config_loader,
            parameter_extractor=self.parameter_extractor,
            parameter_converter=self.parameter_converter,
            parameter_validator=self.parameter_validator
        )

        for level_index, level in enumerate(levels):
            logger.info(f"🔄 执行层级 {level_index + 1}/{len(levels)}: {len(level.tasks)}个任务")

            if level.parallel_groups:
                for group_index, group in enumerate(level.parallel_groups):
                    logger.info(f"  📦 执行并行组 {group_index + 1}/{len(level.parallel_groups)}: {len(group)}个任务")

                    group_results = await asyncio.gather(
                        *[task_executor.execute_task(task, execution_id, all_results) for task in group],
                        return_exceptions=True
                    )

                    for task, result in zip(group, group_results):
                        if isinstance(result, Exception):
                            all_errors[task.tool_name] = str(result)
                            tasks_failed += 1
                            logger.error(f"❌ 任务失败: {task.tool_name}, 错误: {result}")
                        elif isinstance(result, dict) and result.get("skipped"):
                            tasks_skipped += 1
                            all_results[task.tool_name] = result
                            logger.info(f"⏭️ 任务跳过: {task.tool_name}")
                        else:
                            all_results[task.tool_name] = result
                            tasks_completed += 1
                            logger.info(f"✅ 任务完成: {task.tool_name}")
            else:
                for task in level.tasks:
                    result = await task_executor.execute_task(task, execution_id, all_results)
                    if isinstance(result, Exception):
                        all_errors[task.tool_name] = str(result)
                        tasks_failed += 1
                    elif isinstance(result, dict) and result.get("skipped"):
                        tasks_skipped += 1
                        all_results[task.tool_name] = result
                    else:
                        all_results[task.tool_name] = result
                        tasks_completed += 1

        total_time = time.time() - start_time

        return DAGExecutionResult(
            execution_id=execution_id,
            intent_pattern=intent_result.get("intent", intent_result.get("template_id", "unknown")),
            success=tasks_failed == 0,
            total_time=total_time,
            levels_executed=len(levels),
            tasks_completed=tasks_completed,
            tasks_failed=tasks_failed,
            tasks_skipped=tasks_skipped,
            results=all_results,
            errors=all_errors,
            performance_metrics={
                "total_tasks": tasks_completed + tasks_failed + tasks_skipped,
                "success_rate": tasks_completed / max(tasks_completed + tasks_failed + tasks_skipped, 1),
                "average_task_time": total_time / max(tasks_completed + tasks_failed + tasks_skipped, 1)
            }
        )

    # ========================================================================
    # 模板和统计查询方法
    # ========================================================================

    def get_available_templates(self) -> List[Dict[str, Any]]:
        """获取所有可用的DAG模板"""
        templates = []
        for template in self.template_manager.get_all_templates():
            templates.append({
                "template_id": template.template_id,
                "name": template.name,
                "description": template.description,
                "category": template.category.value,
                "complexity_level": template.complexity_level,
                "estimated_duration": template.estimated_duration_seconds,
                "required_tools_count": len(template.required_tools),
                "optional_tools_count": len(template.optional_tools),
                "applicable_intents": template.applicable_intents
            })
        return templates

    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """获取模板详细信息"""
        template = self.template_manager.get_template(template_id)
        if not template:
            return None
        
        return {
            "template_id": template.template_id,
            "name": template.name,
            "description": template.description,
            "category": template.category.value,
            "complexity_level": template.complexity_level,
            "estimated_duration": template.estimated_duration_seconds,
            "required_tools": template.required_tools,
            "optional_tools": template.optional_tools,
            "tool_dependencies": template.tool_dependencies,
            "parallel_groups": template.parallel_groups,
            "expected_output": template.expected_output,
            "safety_constraints": template.safety_constraints,
            "applicable_intents": template.applicable_intents,
            "usage_count": self.performance_stats["template_usage"].get(template_id, 0)
        }

    def get_performance_statistics(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            **self.performance_stats,
            "execution_history": self.execution_history[-10:],
            "tool_usage_stats": self._calculate_tool_usage_stats(),
            "template_statistics": dict(self.performance_stats["template_usage"]),
            "available_templates": len(self.template_manager.get_all_templates())
        }

    def _calculate_tool_usage_stats(self) -> Dict[str, int]:
        """计算工具使用统计"""
        stats = defaultdict(int)
        for execution in self.execution_history:
            pass  # 可以从execution中提取工具使用信息
        return dict(stats)

    def get_execution_logs(
        self,
        tool_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Any]:
        """获取执行日志"""
        if self.visualizer:
            return self.visualizer.get_execution_logs(tool_name, status, limit)
        return []

    def generate_execution_summary(self) -> str:
        """生成执行摘要"""
        if self.visualizer:
            return self.visualizer.generate_execution_summary()
        return "Visualizer not available"

    def export_execution_logs(self, filepath: str):
        """导出执行日志到文件"""
        if self.visualizer:
            self.visualizer.export_logs_to_file(filepath)
