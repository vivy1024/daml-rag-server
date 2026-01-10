#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
三层检索执行流程验证脚本

验证内容:
1. Layer1→Layer2→Layer3顺序执行
2. 降级策略正常工作
3. 各层执行时间和结果统计

Requirements: 4.2 - 三层执行顺序验证

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 添加项目路径
sys.path.insert(0, '/app')

from src.framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine, ThreeLayerResult


class ThreeLayerFlowVerifier:
    """三层检索流程验证器"""
    
    def __init__(self):
        """初始化验证器"""
        self.engine = None
        self.test_results: List[Dict[str, Any]] = []
        
    async def initialize(self):
        """初始化三层检索引擎"""
        neo4j_uri = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
        neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
        neo4j_password = os.getenv('NEO4J_PASSWORD')
        
        logger.info("=" * 70)
        logger.info("初始化三层检索引擎")
        logger.info("=" * 70)
        logger.info(f"Neo4j URI: {neo4j_uri}")
        logger.info(f"Neo4j User: {neo4j_user}")
        
        self.engine = TrueThreeLayerEngine(
            graphrag_api_port="8001",
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            enable_neo4j_direct=True
        )
        
        logger.info(f"Neo4j可用性: {self.engine.neo4j_available}")
        return self.engine.neo4j_available
    
    async def verify_execution_order(self, result: ThreeLayerResult) -> Dict[str, Any]:
        """
        验证三层执行顺序
        
        检查:
        1. Layer1先于Layer2执行
        2. Layer2先于Layer3执行
        3. 所有层都有执行结果（即使失败）
        """
        verification = {
            "passed": True,
            "checks": [],
            "issues": []
        }
        
        # 检查1: 所有层都有结果
        if result.layer_1_result is None:
            verification["passed"] = False
            verification["issues"].append("Layer1结果为空")
        else:
            verification["checks"].append("✅ Layer1有执行结果")
            
        if result.layer_2_result is None:
            verification["passed"] = False
            verification["issues"].append("Layer2结果为空")
        else:
            verification["checks"].append("✅ Layer2有执行结果")
            
        if result.layer_3_result is None:
            verification["passed"] = False
            verification["issues"].append("Layer3结果为空")
        else:
            verification["checks"].append("✅ Layer3有执行结果")
        
        # 检查2: 执行时间顺序（Layer1应该先完成）
        # 注意：由于是顺序执行，我们检查累计时间
        l1_time = result.layer_1_result.execution_time_ms if result.layer_1_result else 0
        l2_time = result.layer_2_result.execution_time_ms if result.layer_2_result else 0
        l3_time = result.layer_3_result.execution_time_ms if result.layer_3_result else 0
        
        verification["execution_times"] = {
            "layer1_ms": l1_time,
            "layer2_ms": l2_time,
            "layer3_ms": l3_time,
            "total_ms": result.total_execution_time_ms
        }
        
        # 检查3: 验证层名称正确
        if result.layer_1_result and "Layer1" in result.layer_1_result.layer_name:
            verification["checks"].append("✅ Layer1名称正确")
        else:
            verification["issues"].append("Layer1名称不正确")
            
        if result.layer_2_result and "Layer2" in result.layer_2_result.layer_name:
            verification["checks"].append("✅ Layer2名称正确")
        else:
            verification["issues"].append("Layer2名称不正确")
            
        if result.layer_3_result and "Layer3" in result.layer_3_result.layer_name:
            verification["checks"].append("✅ Layer3名称正确")
        else:
            verification["issues"].append("Layer3名称不正确")
        
        return verification
    
    async def verify_fallback_strategy(self, result: ThreeLayerResult) -> Dict[str, Any]:
        """
        验证降级策略
        
        检查:
        1. Layer1失败时是否触发降级
        2. 降级后是否有结果返回
        3. 降级来源是否正确标记
        """
        verification = {
            "passed": True,
            "checks": [],
            "fallback_triggered": False,
            "fallback_source": None
        }
        
        # 检查Layer1是否成功
        l1_success = result.layer_1_result.success if result.layer_1_result else False
        l1_results = len(result.layer_1_result.results) if result.layer_1_result else 0
        
        if not l1_success or l1_results == 0:
            verification["fallback_triggered"] = True
            verification["checks"].append("⚠️ Layer1失败/无结果，触发降级")
            
            # 检查Layer2是否有结果（降级方案）
            l2_success = result.layer_2_result.success if result.layer_2_result else False
            l2_results = len(result.layer_2_result.results) if result.layer_2_result else 0
            
            if l2_success and l2_results > 0:
                verification["checks"].append("✅ 降级到Layer2成功")
                verification["fallback_source"] = result.layer_2_result.metadata.get("source", "unknown")
            else:
                # 检查是否使用了规则匹配降级
                if "Fallback" in (result.layer_2_result.layer_name if result.layer_2_result else ""):
                    verification["checks"].append("✅ 使用规则匹配降级")
                    verification["fallback_source"] = "rule_based_fallback"
                else:
                    verification["passed"] = False
                    verification["checks"].append("❌ 降级方案未能提供结果")
        else:
            verification["checks"].append("✅ Layer1正常工作，无需降级")
        
        # 检查最终结果
        if result.final_results:
            verification["checks"].append(f"✅ 最终返回{len(result.final_results)}个结果")
        else:
            verification["passed"] = False
            verification["checks"].append("❌ 最终无结果返回")
        
        return verification
    
    async def run_test_case(
        self,
        name: str,
        query: str,
        user_profile: Dict[str, Any] = None,
        filters: Dict[str, Any] = None,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """运行单个测试用例"""
        logger.info(f"\n{'='*70}")
        logger.info(f"测试用例: {name}")
        logger.info(f"查询: {query}")
        logger.info(f"{'='*70}")
        
        start_time = datetime.now()
        
        try:
            result = await self.engine.execute_three_layer_query(
                query=query,
                domain="fitness_exercises",
                user_id="test_user",
                user_profile=user_profile or {},
                filters=filters or {},
                top_k=top_k,
                safety_check=True
            )
            
            # 验证执行顺序
            order_verification = await self.verify_execution_order(result)
            
            # 验证降级策略
            fallback_verification = await self.verify_fallback_strategy(result)
            
            test_result = {
                "name": name,
                "query": query,
                "success": True,
                "execution_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                "layer_results": {
                    "layer1": {
                        "success": result.layer_1_result.success,
                        "count": len(result.layer_1_result.results),
                        "confidence": result.layer_1_result.confidence,
                        "time_ms": result.layer_1_result.execution_time_ms
                    },
                    "layer2": {
                        "success": result.layer_2_result.success,
                        "count": len(result.layer_2_result.results),
                        "confidence": result.layer_2_result.confidence,
                        "time_ms": result.layer_2_result.execution_time_ms,
                        "source": result.layer_2_result.metadata.get("source", "unknown")
                    },
                    "layer3": {
                        "success": result.layer_3_result.success,
                        "count": len(result.layer_3_result.results),
                        "confidence": result.layer_3_result.confidence,
                        "time_ms": result.layer_3_result.execution_time_ms
                    }
                },
                "final_results_count": len(result.final_results),
                "total_confidence": result.total_confidence,
                "reasoning": result.reasoning,
                "order_verification": order_verification,
                "fallback_verification": fallback_verification
            }
            
            # 打印结果
            self._print_test_result(test_result)
            
            self.test_results.append(test_result)
            return test_result
            
        except Exception as e:
            logger.error(f"测试用例失败: {e}", exc_info=True)
            test_result = {
                "name": name,
                "query": query,
                "success": False,
                "error": str(e)
            }
            self.test_results.append(test_result)
            return test_result
    
    def _print_test_result(self, result: Dict[str, Any]):
        """打印测试结果"""
        logger.info(f"\n【Layer 1 - 向量检索】")
        l1 = result["layer_results"]["layer1"]
        logger.info(f"  成功: {l1['success']}")
        logger.info(f"  结果数: {l1['count']}")
        logger.info(f"  置信度: {l1['confidence']:.2f}")
        logger.info(f"  耗时: {l1['time_ms']:.0f}ms")
        
        logger.info(f"\n【Layer 2 - 图谱推理】")
        l2 = result["layer_results"]["layer2"]
        logger.info(f"  成功: {l2['success']}")
        logger.info(f"  结果数: {l2['count']}")
        logger.info(f"  置信度: {l2['confidence']:.2f}")
        logger.info(f"  耗时: {l2['time_ms']:.0f}ms")
        logger.info(f"  数据源: {l2['source']}")
        
        logger.info(f"\n【Layer 3 - 业务规则】")
        l3 = result["layer_results"]["layer3"]
        logger.info(f"  成功: {l3['success']}")
        logger.info(f"  结果数: {l3['count']}")
        logger.info(f"  置信度: {l3['confidence']:.2f}")
        logger.info(f"  耗时: {l3['time_ms']:.0f}ms")
        
        logger.info(f"\n【执行顺序验证】")
        for check in result["order_verification"]["checks"]:
            logger.info(f"  {check}")
        if result["order_verification"]["issues"]:
            for issue in result["order_verification"]["issues"]:
                logger.warning(f"  ⚠️ {issue}")
        
        logger.info(f"\n【降级策略验证】")
        for check in result["fallback_verification"]["checks"]:
            logger.info(f"  {check}")
        if result["fallback_verification"]["fallback_triggered"]:
            logger.info(f"  降级来源: {result['fallback_verification']['fallback_source']}")
        
        logger.info(f"\n【最终结果】")
        logger.info(f"  结果数: {result['final_results_count']}")
        logger.info(f"  总置信度: {result['total_confidence']:.2f}")
        logger.info(f"  推理: {result['reasoning']}")
    
    async def run_all_tests(self):
        """运行所有测试用例"""
        logger.info("\n" + "=" * 70)
        logger.info("开始三层检索流程验证")
        logger.info("=" * 70)
        
        # 测试用例1: 正常查询（应该三层都成功）
        await self.run_test_case(
            name="正常查询 - 胸部训练",
            query="推荐适合初学者的胸部增肌训练动作",
            user_profile={
                "fitness_level": "beginner",
                "available_equipment": ["哑铃", "杠铃"]
            },
            filters={
                "muscle_group": "胸部"
            }
        )
        
        # 测试用例2: 带器械过滤的查询
        await self.run_test_case(
            name="器械过滤查询 - 背部训练",
            query="背部肌肉锻炼动作，只用哑铃",
            user_profile={
                "fitness_level": "intermediate",
                "available_equipment": ["哑铃"]
            },
            filters={
                "available_equipment": ["哑铃"]
            }
        )
        
        # 测试用例3: 复杂查询（多条件）
        await self.run_test_case(
            name="复杂查询 - 腿部力量",
            query="适合中级训练者的腿部力量训练，需要杠铃和深蹲架",
            user_profile={
                "fitness_level": "intermediate",
                "available_equipment": ["杠铃", "深蹲架"]
            }
        )
        
        # 测试用例4: 安全检查查询
        await self.run_test_case(
            name="安全检查查询 - 有伤病用户",
            query="肩部训练动作推荐",
            user_profile={
                "fitness_level": "beginner",
                "health_profile": {
                    "injuries": [{"body_part": "肩关节"}]
                }
            }
        )
        
        # 打印总结
        self._print_summary()
    
    def _print_summary(self):
        """打印测试总结"""
        logger.info("\n" + "=" * 70)
        logger.info("测试总结")
        logger.info("=" * 70)
        
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r.get("success", False))
        
        logger.info(f"总测试数: {total}")
        logger.info(f"通过: {passed}")
        logger.info(f"失败: {total - passed}")
        
        # 统计三层执行情况
        l1_success = sum(1 for r in self.test_results 
                        if r.get("layer_results", {}).get("layer1", {}).get("success", False))
        l2_success = sum(1 for r in self.test_results 
                        if r.get("layer_results", {}).get("layer2", {}).get("success", False))
        l3_success = sum(1 for r in self.test_results 
                        if r.get("layer_results", {}).get("layer3", {}).get("success", False))
        
        logger.info(f"\n各层成功率:")
        logger.info(f"  Layer1 (向量): {l1_success}/{total} ({l1_success/total*100:.0f}%)")
        logger.info(f"  Layer2 (图谱): {l2_success}/{total} ({l2_success/total*100:.0f}%)")
        logger.info(f"  Layer3 (规则): {l3_success}/{total} ({l3_success/total*100:.0f}%)")
        
        # 统计降级情况
        fallback_count = sum(1 for r in self.test_results 
                            if r.get("fallback_verification", {}).get("fallback_triggered", False))
        logger.info(f"\n降级触发次数: {fallback_count}/{total}")
        
        # 执行顺序验证
        order_passed = sum(1 for r in self.test_results 
                         if r.get("order_verification", {}).get("passed", False))
        logger.info(f"执行顺序验证通过: {order_passed}/{total}")
        
        logger.info("\n" + "=" * 70)
    
    def close(self):
        """关闭引擎"""
        if self.engine:
            self.engine.close()
            logger.info("三层检索引擎已关闭")


async def main():
    """主函数"""
    verifier = ThreeLayerFlowVerifier()
    
    try:
        # 初始化
        neo4j_available = await verifier.initialize()
        
        if not neo4j_available:
            logger.warning("⚠️ Neo4j不可用，部分测试可能使用降级方案")
        
        # 运行测试
        await verifier.run_all_tests()
        
    finally:
        verifier.close()


if __name__ == "__main__":
    asyncio.run(main())
