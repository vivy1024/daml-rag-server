#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
MCP工具集成验证脚本

验证12个新MCP工具是否正确集成到DAML-RAG编排系统中。

测试内容:
1. 工具类导入测试
2. 工具实例化测试
3. DAG节点调用测试
4. MCPOrchestrator集成测试

作者: 薛小川
版本: v1.0.0
日期: 2025-12-01
"""

import sys
import os
import asyncio
import logging
from typing import Dict, Any

# 设置路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_tool_imports() -> bool:
    """测试12个工具类是否可以正确导入"""
    logger.info("🔍 测试工具类导入...")

    tools_to_test = [
        ("IntelligentExerciseSelector", "intelligent_exercise_selector"),
        ("ExerciseSimilarityFinder", "exercise_similarity_finder"),
        ("SafeExerciseModifier", "safe_exercise_modifier"),
        ("PeriodizedProgramDesigner", "periodized_program_designer"),
        ("MuscleGroupVolumeCalculator", "muscle_group_volume_calculator"),
        ("MovementPatternBalancer", "movement_pattern_balancer"),
        ("InjuryRiskAssessor", "injury_risk_assessor"),
        ("ContraindicationsChecker", "contraindications_checker"),
        ("ExerciseNutritionOptimizer", "exercise_nutrition_optimization"),
        ("MuscleRecoveryNutrition", "muscle_recovery_nutrition"),
        ("TrainingAnalyticsDashboard", "training_analytics_dashboard"),
        ("EvidenceBasedRecommender", "evidence_based_recommender")
    ]

    failed_imports = []
    successful_imports = []

    for class_name, module_name in tools_to_test:
        try:
            from applications.fitness.tools import locals()[class_name]
            successful_imports.append(class_name)
            logger.info(f"  ✅ {class_name} - 导入成功")
        except ImportError as e:
            failed_imports.append((class_name, str(e)))
            logger.error(f"  ❌ {class_name} - 导入失败: {e}")
        except Exception as e:
            failed_imports.append((class_name, str(e)))
            logger.error(f"  ❌ {class_name} - 未知错误: {e}")

    logger.info(f"\n📊 导入测试结果:")
    logger.info(f"  成功: {len(successful_imports)}/12")
    logger.info(f"  失败: {len(failed_imports)}/12")

    if failed_imports:
        logger.error("\n❌ 失败的导入:")
        for class_name, error in failed_imports:
            logger.error(f"  - {class_name}: {error}")
        return False

    logger.info("\n✅ 所有工具导入成功!")
    return True


def test_orchestrator_tool_list() -> bool:
    """测试MCPOrchestrator是否包含新工具"""
    logger.info("\n🔍 测试MCPOrchestrator工具列表...")

    try:
        from framework.orchestration.mcp_orchestrator import MCPOrchestrator

        # 读取MCPOrchestrator源码，检查工具列表
        orchestrator_file = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'framework', 'orchestration', 'mcp_orchestrator.py'
        )

        with open(orchestrator_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查12个新工具是否在工具列表中
        new_tools = [
            "intelligent_exercise_selector",
            "exercise_similarity_finder",
            "safe_exercise_modifier",
            "periodized_program_designer",
            "muscle_group_volume_calculator",
            "movement_pattern_balancer",
            "injury_risk_assessor",
            "contraindications_checker",
            "exercise_nutrition_optimization",
            "muscle_recovery_nutrition",
            "training_analytics_dashboard",
            "evidence_based_recommender"
        ]

        missing_tools = []
        found_tools = []

        for tool in new_tools:
            if f'"{tool}"' in content:
                found_tools.append(tool)
                logger.info(f"  ✅ {tool} - 已集成")
            else:
                missing_tools.append(tool)
                logger.error(f"  ❌ {tool} - 未找到")

        logger.info(f"\n📊 工具集成测试结果:")
        logger.info(f"  已集成: {len(found_tools)}/12")
        logger.info(f"  未集成: {len(missing_tools)}/12")

        if missing_tools:
            logger.error("\n❌ 未集成的工具:")
            for tool in missing_tools:
                logger.error(f"  - {tool}")
            return False

        logger.info("\n✅ 所有工具已集成到MCPOrchestrator!")
        return True

    except Exception as e:
        logger.error(f"❌ 工具列表测试失败: {e}")
        return False


async def test_tool_mock_execution() -> bool:
    """测试工具的模拟执行（不连接真实数据库）"""
    logger.info("\n🔍 测试工具模拟执行...")

    try:
        # 测试智能动作选择器
        from applications.fitness.tools import IntelligentExerciseSelector

        # 创建模拟的Neo4j客户端
        class MockNeo4jClient:
            async def aquery(self, query, params=None):
                return []

        mock_client = MockNeo4jClient()
        tool = IntelligentExerciseSelector(mock_client)

        # 测试执行（使用最小参数）
        result = await tool.execute({
            "training_goal": "hypertrophy",
            "user_level": "intermediate",
            "limit": 5
        })

        # 验证返回格式
        if not isinstance(result, dict):
            logger.error("  ❌ 返回结果不是字典格式")
            return False

        required_fields = ["tool", "status", "execution_time_ms"]
        for field in required_fields:
            if field not in result:
                logger.error(f"  ❌ 缺少必需字段: {field}")
                return False

        logger.info(f"  ✅ IntelligentExerciseSelector 执行成功")
        logger.info(f"    - 状态: {result.get('status')}")
        logger.info(f"    - 执行时间: {result.get('execution_time_ms', 0):.2f}ms")

        logger.info("\n✅ 工具模拟执行测试通过!")
        return True

    except Exception as e:
        logger.error(f"❌ 工具模拟执行测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tools_module_init() -> bool:
    """测试tools模块的__init__.py是否正确导出所有工具"""
    logger.info("\n🔍 测试tools模块导出...")

    try:
        from applications.fitness import tools

        # 检查__all__是否定义
        if not hasattr(tools, '__all__'):
            logger.error("  ❌ tools模块未定义__all__")
            return False

        expected_tools = [
            "IntelligentExerciseSelector",
            "ExerciseSimilarityFinder",
            "SafeExerciseModifier",
            "PeriodizedProgramDesigner",
            "MuscleGroupVolumeCalculator",
            "MovementPatternBalancer",
            "InjuryRiskAssessor",
            "ContraindicationsChecker",
            "ExerciseNutritionOptimizer",
            "MuscleRecoveryNutrition",
            "TrainingAnalyticsDashboard",
            "EvidenceBasedRecommender"
        ]

        missing_tools = []
        for tool_name in expected_tools:
            if tool_name not in tools.__all__:
                missing_tools.append(tool_name)
                logger.error(f"  ❌ __all__中缺少: {tool_name}")
            else:
                logger.info(f"  ✅ {tool_name} - 已导出")

        if missing_tools:
            logger.error(f"\n❌ 缺少{len(missing_tools)}个工具导出")
            return False

        logger.info(f"\n✅ 所有{len(expected_tools)}个工具正确导出!")
        return True

    except Exception as e:
        logger.error(f"❌ tools模块导出测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    logger.info("=" * 80)
    logger.info("🧪 MCP工具集成验证开始")
    logger.info("=" * 80)

    test_results = []

    # 测试1: 工具导入
    test_results.append(("工具导入测试", test_tool_imports()))

    # 测试2: 模块导出
    test_results.append(("模块导出测试", test_tools_module_init()))

    # 测试3: Orchestrator集成
    test_results.append(("Orchestrator集成测试", test_orchestrator_tool_list()))

    # 测试4: 模拟执行
    test_results.append(("模拟执行测试", await test_tool_mock_execution()))

    # 汇总结果
    logger.info("\n" + "=" * 80)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 80)

    passed = 0
    failed = 0

    for test_name, result in test_results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"{status} - {test_name}")
        if result:
            passed += 1
        else:
            failed += 1

    logger.info("-" * 80)
    logger.info(f"总计: {passed + failed} 项测试")
    logger.info(f"通过: {passed} 项")
    logger.info(f"失败: {failed} 项")
    logger.info("=" * 80)

    if failed == 0:
        logger.info("\n🎉 所有测试通过! MCP工具集成成功!")
        return 0
    else:
        logger.error(f"\n⚠️  {failed}项测试失败，请检查集成问题")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
