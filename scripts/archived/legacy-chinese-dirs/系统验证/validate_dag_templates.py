#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DAG模板执行验证脚本 - 真实环境测试

验证需求: Requirements 9.1, 9.2, 9.3, 9.4, 9.5
"""

import asyncio
import sys
import os
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def main():
    logger.info("="*80)
    logger.info("🚀 DAG模板执行验证")
    logger.info("="*80)
    
    try:
        from src.applications.fitness.dag_template_system import DAGTemplateManager
        from src.applications.fitness.enhanced_dag_orchestrator import EnhancedDAGOrchestrator
        from src.framework.orchestration.mcp_orchestrator import MCPOrchestrator
        from src.framework.storage.metadata_database import MetadataDB
        from src.framework.clients.mcp_client_v2 import ConfigurableMCPClient
        
        # 初始化
        logger.info("初始化组件...")
        template_manager = DAGTemplateManager()
        logger.info(f"✅ 加载了 {len(template_manager.get_all_templates())} 个DAG模板")
        
        mcp_client = ConfigurableMCPClient()
        await mcp_client.connect()
        logger.info("✅ MCP客户端连接成功")
        
        metadata_db = MetadataDB(db_path="/tmp/dag_validation.db")
        mcp_orchestrator = MCPOrchestrator(metadata_db=metadata_db, mcp_client_pool=mcp_client)
        
        dag_orchestrator = EnhancedDAGOrchestrator(
            mcp_orchestrator=mcp_orchestrator,
            template_manager=template_manager
        )
        logger.info("✅ DAG编排器初始化成功\n")

        
        # 测试数据
        user_profile = {
            "user_id": 1, "age": 30, "gender": "male", "weight": 75, "height": 175,
            "fitness_level": "intermediate", "fitness_goals": ["增肌"],
            "health_conditions": [], "available_equipment": ["哑铃", "杠铃"]
        }
        
        results = []
        
        # 测试10.1: complete_training_plan
        logger.info("="*80)
        logger.info("测试10.1: complete_training_plan模板")
        logger.info("="*80)
        try:
            start = time.time()
            result = await dag_orchestrator.execute_template(
                template_id="complete_training_plan",
                user_profile=user_profile,
                session_context={"session_id": "test1", "query": "制定训练计划"}
            )
            exec_time = time.time() - start
            logger.info(f"✅ 执行成功 - 时间: {exec_time:.2f}秒, 完成: {result.tasks_completed}个任务")
            results.append(("10.1 complete_training_plan", True, exec_time))
        except Exception as e:
            logger.error(f"❌ 失败: {e}")
            results.append(("10.1 complete_training_plan", False, 0))
        
        # 测试10.2: nutrition_planning
        logger.info("\n" + "="*80)
        logger.info("测试10.2: nutrition_planning模板")
        logger.info("="*80)
        try:
            start = time.time()
            result = await dag_orchestrator.execute_template(
                template_id="nutrition_planning",
                user_profile=user_profile,
                session_context={"session_id": "test2", "query": "制定营养计划"}
            )
            exec_time = time.time() - start
            logger.info(f"✅ 执行成功 - 时间: {exec_time:.2f}秒, 完成: {result.tasks_completed}个任务")
            results.append(("10.2 nutrition_planning", True, exec_time))
        except Exception as e:
            logger.error(f"❌ 失败: {e}")
            results.append(("10.2 nutrition_planning", False, 0))

        
        # 测试10.3: safety_assessment
        logger.info("\n" + "="*80)
        logger.info("测试10.3: safety_assessment模板")
        logger.info("="*80)
        try:
            user_profile_with_injury = user_profile.copy()
            user_profile_with_injury["health_conditions"] = ["腰部拉伤"]
            start = time.time()
            result = await dag_orchestrator.execute_template(
                template_id="safety_assessment",
                user_profile=user_profile_with_injury,
                session_context={"session_id": "test3", "query": "安全评估"}
            )
            exec_time = time.time() - start
            logger.info(f"✅ 执行成功 - 时间: {exec_time:.2f}秒, 完成: {result.tasks_completed}个任务")
            results.append(("10.3 safety_assessment", True, exec_time))
        except Exception as e:
            logger.error(f"❌ 失败: {e}")
            results.append(("10.3 safety_assessment", False, 0))
        
        # 测试10.4: 所有8个模板
        logger.info("\n" + "="*80)
        logger.info("测试10.4: 测试所有8个DAG模板")
        logger.info("="*80)
        
        all_templates = template_manager.get_all_templates()
        template_results = []
        
        for template in all_templates:
            logger.info(f"\n测试: {template.name} ({template.template_id})")
            try:
                start = time.time()
                result = await dag_orchestrator.execute_template(
                    template_id=template.template_id,
                    user_profile=user_profile,
                    session_context={"session_id": f"test_{template.template_id}", "query": "测试"}
                )
                exec_time = time.time() - start
                logger.info(f"  ✅ 成功 - {exec_time:.2f}秒, {result.tasks_completed}个任务")
                template_results.append((template.name, True, exec_time))
            except Exception as e:
                logger.error(f"  ❌ 失败: {e}")
                template_results.append((template.name, False, 0))
        
        success_count = sum(1 for _, success, _ in template_results if success)
        logger.info(f"\n所有模板测试: {success_count}/{len(template_results)} 成功")
        results.append(("10.4 all_templates", success_count >= len(template_results) * 0.8, 0))

        
        # 打印摘要
        logger.info("\n" + "="*80)
        logger.info("📊 验证结果汇总")
        logger.info("="*80)
        passed = sum(1 for _, success, _ in results if success)
        for test_name, success, exec_time in results:
            status = "✅" if success else "❌"
            time_str = f" ({exec_time:.2f}秒)" if exec_time > 0 else ""
            logger.info(f"{status} {test_name}{time_str}")
        logger.info("="*80)
        logger.info(f"总计: {passed}/{len(results)} 测试通过")
        logger.info("="*80)
        
        await mcp_client.disconnect()
        
        return 0 if passed == len(results) else 1
        
    except Exception as e:
        logger.error(f"❌ 验证异常: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
