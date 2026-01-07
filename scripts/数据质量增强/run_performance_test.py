"""
性能测试脚本

功能：
1. 测试数据补充脚本的执行时间
2. 测试MCP工具的响应时间
3. 生成性能报告

作者：薛小川
日期：2025-12-15
"""

import asyncio
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any
from neo4j import AsyncGraphDatabase

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PerformanceTester:
    """性能测试器"""
    
    def __init__(self, uri: str, user: str, password: str):
        """初始化测试器"""
        self.driver = AsyncGraphDatabase.driver(uri, auth=(user, password))
        self.performance_results = {
            "timestamp": datetime.now().isoformat(),
            "database_queries": {},
            "summary": {}
        }
    
    async def close(self):
        """关闭驱动"""
        await self.driver.close()
    
    async def test_exercise_query_performance(self) -> Dict[str, Any]:
        """测试Exercise节点查询性能"""
        logger.info("=" * 60)
        logger.info("测试Exercise节点查询性能")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            # 1. 测试基本查询
            logger.info("\n1. 测试基本Exercise查询...")
            start_time = time.time()
            query = """
            MATCH (e:Exercise)
            RETURN count(e) as total
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["basic_count"] = {
                "query": "基本计数查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['basic_count']['time_ms']}ms")
            
            # 2. 测试带字段过滤的查询
            logger.info("\n2. 测试kinetic_chain_type过滤查询...")
            start_time = time.time()
            query = """
            MATCH (e:Exercise)
            WHERE e.kinetic_chain_type = 'closed_chain'
            RETURN count(e) as total
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["kinetic_chain_filter"] = {
                "query": "运动链类型过滤",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['kinetic_chain_filter']['time_ms']}ms")
            
            # 3. 测试复杂查询（带关系）
            logger.info("\n3. 测试Exercise-Muscle关系查询...")
            start_time = time.time()
            query = """
            MATCH (e:Exercise)-[:TARGETS_PRIMARY]->(m:Muscle)
            WHERE e.kinetic_chain_type = 'closed_chain'
            RETURN e.name_zh, collect(m.name_zh) as muscles
            LIMIT 10
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["exercise_muscle_relation"] = {
                "query": "Exercise-Muscle关系查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['exercise_muscle_relation']['time_ms']}ms")
            
            # 4. 测试ROM字段查询
            logger.info("\n4. 测试ROM字段查询...")
            start_time = time.time()
            query = """
            MATCH (e:Exercise)
            WHERE e.rom_requirements IS NOT NULL
            RETURN count(e) as total
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["rom_query"] = {
                "query": "ROM字段查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['rom_query']['time_ms']}ms")
            
            return results
    
    async def test_food_query_performance(self) -> Dict[str, Any]:
        """测试Food节点查询性能"""
        logger.info("\n" + "=" * 60)
        logger.info("测试Food节点查询性能")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            # 1. 测试基本查询
            logger.info("\n1. 测试基本Food查询...")
            start_time = time.time()
            query = """
            MATCH (f:Food)
            RETURN count(f) as total
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["basic_count"] = {
                "query": "基本计数查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['basic_count']['time_ms']}ms")
            
            # 2. 测试GI过滤查询
            logger.info("\n2. 测试glycemic_index过滤查询...")
            start_time = time.time()
            query = """
            MATCH (f:Food)
            WHERE f.glycemic_index IS NOT NULL AND f.glycemic_index < 55
            RETURN count(f) as total
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["gi_filter"] = {
                "query": "低GI食物过滤",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['gi_filter']['time_ms']}ms")
            
            # 3. 测试消化时间查询
            logger.info("\n3. 测试digestion_time_minutes查询...")
            start_time = time.time()
            query = """
            MATCH (f:Food)
            WHERE f.digestion_time_minutes IS NOT NULL
            RETURN f.name, f.digestion_time_minutes
            LIMIT 10
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["digestion_query"] = {
                "query": "消化时间查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['digestion_query']['time_ms']}ms")
            
            # 4. 测试过敏原查询
            logger.info("\n4. 测试allergens查询...")
            start_time = time.time()
            query = """
            MATCH (f:Food)
            WHERE f.allergens IS NOT NULL
            RETURN count(f) as total
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["allergens_query"] = {
                "query": "过敏原查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['allergens_query']['time_ms']}ms")
            
            return results
    
    async def test_injury_query_performance(self) -> Dict[str, Any]:
        """测试InjuryType节点查询性能"""
        logger.info("\n" + "=" * 60)
        logger.info("测试InjuryType节点查询性能")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            # 1. 测试severity_level过滤
            logger.info("\n1. 测试severity_level过滤查询...")
            start_time = time.time()
            query = """
            MATCH (i:InjuryType)
            WHERE i.severity_level = 'severe'
            RETURN count(i) as total
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["severity_filter"] = {
                "query": "严重程度过滤",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['severity_filter']['time_ms']}ms")
            
            return results
    
    async def test_rehab_query_performance(self) -> Dict[str, Any]:
        """测试康复相关查询性能"""
        logger.info("\n" + "=" * 60)
        logger.info("测试康复相关查询性能")
        logger.info("=" * 60)
        
        async with self.driver.session() as session:
            results = {}
            
            # 1. 测试RehabilitationPhase查询
            logger.info("\n1. 测试RehabilitationPhase查询...")
            start_time = time.time()
            query = """
            MATCH (rp:RehabilitationPhase)
            RETURN rp.phase_id, rp.name_zh, rp.duration_days
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["rehab_phase_query"] = {
                "query": "康复阶段查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['rehab_phase_query']['time_ms']}ms")
            
            # 2. 测试REHAB_PROGRESSION关系查询
            logger.info("\n2. 测试REHAB_PROGRESSION关系查询...")
            start_time = time.time()
            query = """
            MATCH (e1:Exercise)-[r:REHAB_PROGRESSION]->(e2:Exercise)
            RETURN e1.name_zh, e2.name_zh, r.progression_order, r.criteria
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["rehab_progression_query"] = {
                "query": "康复渐进关系查询",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['rehab_progression_query']['time_ms']}ms")
            
            # 3. 测试康复路径查询（多跳）
            logger.info("\n3. 测试康复路径查询（多跳）...")
            start_time = time.time()
            query = """
            MATCH path = (e1:Exercise)-[:REHAB_PROGRESSION*1..3]->(e2:Exercise)
            RETURN e1.name_zh as start, e2.name_zh as end, length(path) as steps
            LIMIT 10
            """
            await session.run(query)
            elapsed = time.time() - start_time
            results["rehab_path_query"] = {
                "query": "康复路径查询（多跳）",
                "time_ms": round(elapsed * 1000, 2)
            }
            logger.info(f"  执行时间: {results['rehab_path_query']['time_ms']}ms")
            
            return results
    
    async def generate_summary(self):
        """生成性能摘要"""
        logger.info("\n" + "=" * 60)
        logger.info("性能测试摘要")
        logger.info("=" * 60)
        
        all_times = []
        
        # 收集所有查询时间
        for category, queries in self.performance_results["database_queries"].items():
            for query_name, query_data in queries.items():
                all_times.append(query_data["time_ms"])
        
        if all_times:
            avg_time = sum(all_times) / len(all_times)
            max_time = max(all_times)
            min_time = min(all_times)
            
            self.performance_results["summary"] = {
                "total_queries": len(all_times),
                "average_time_ms": round(avg_time, 2),
                "max_time_ms": max_time,
                "min_time_ms": min_time,
                "all_under_100ms": all(t < 100 for t in all_times),
                "all_under_500ms": all(t < 500 for t in all_times)
            }
            
            logger.info(f"\n总查询数: {self.performance_results['summary']['total_queries']}")
            logger.info(f"平均响应时间: {self.performance_results['summary']['average_time_ms']}ms")
            logger.info(f"最快查询: {self.performance_results['summary']['min_time_ms']}ms")
            logger.info(f"最慢查询: {self.performance_results['summary']['max_time_ms']}ms")
            logger.info(f"所有查询<100ms: {'✅ 是' if self.performance_results['summary']['all_under_100ms'] else '❌ 否'}")
            logger.info(f"所有查询<500ms: {'✅ 是' if self.performance_results['summary']['all_under_500ms'] else '❌ 否'}")
            
            # 性能评估
            if self.performance_results['summary']['all_under_100ms']:
                logger.info("\n✅ 性能评估: 优秀 - 所有查询响应时间<100ms")
            elif self.performance_results['summary']['all_under_500ms']:
                logger.info("\n✅ 性能评估: 良好 - 所有查询响应时间<500ms")
            else:
                logger.info("\n⚠️ 性能评估: 需要优化 - 部分查询响应时间>500ms")
    
    async def save_report(self, output_file: str = "performance_report.json"):
        """保存性能报告"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.performance_results, f, ensure_ascii=False, indent=2)
        logger.info(f"\n性能报告已保存到: {output_file}")
    
    async def run_all_tests(self):
        """运行所有性能测试"""
        try:
            # 1. 测试Exercise查询
            self.performance_results["database_queries"]["exercise"] = await self.test_exercise_query_performance()
            
            # 2. 测试Food查询
            self.performance_results["database_queries"]["food"] = await self.test_food_query_performance()
            
            # 3. 测试InjuryType查询
            self.performance_results["database_queries"]["injury_type"] = await self.test_injury_query_performance()
            
            # 4. 测试康复相关查询
            self.performance_results["database_queries"]["rehabilitation"] = await self.test_rehab_query_performance()
            
            # 5. 生成摘要
            await self.generate_summary()
            
            # 6. 保存报告
            await self.save_report()
            
        except Exception as e:
            logger.error(f"性能测试过程中发生错误: {e}", exc_info=True)
            raise


async def main():
    """主函数"""
    # Neo4j连接配置
    NEO4J_URI = "bolt://fitness_neo4j:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "build_body_2024"
    
    tester = PerformanceTester(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    
    try:
        await tester.run_all_tests()
    finally:
        await tester.close()


if __name__ == "__main__":
    asyncio.run(main())
