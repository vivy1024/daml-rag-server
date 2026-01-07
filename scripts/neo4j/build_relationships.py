# -*- coding: utf-8 -*-
"""
Neo4j Exercise关系构建脚本

构建Exercise与分类节点的关系：
- USES_FORCE: Exercise -> ForceType
- HAS_MECHANIC: Exercise -> MechanicType
- HAS_KINETIC_CHAIN: Exercise -> KineticChain
- USES_GRIP: Exercise -> GripType
- SUITABLE_FOR_LEVEL: Exercise -> TrainingLevel

版本: v1.0.0
日期: 2026-01-05
Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6
"""

import sys
import os
import json
import logging
from typing import Dict, Any, List, Tuple
from dataclasses import dataclass

# 添加项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 属性值映射（数据源值 -> Neo4j节点name）
FORCE_MAPPING = {
    "Push": "push",
    "Pull": "pull",
    "Hold": "hold",
    "push": "push",
    "pull": "pull",
    "hold": "hold",
}

MECHANIC_MAPPING = {
    "Compound": "compound",
    "Isolation": "isolation",
    "compound": "compound",
    "isolation": "isolation",
}

KINETIC_CHAIN_MAPPING = {
    "open_chain": "open_chain",
    "closed_chain": "closed_chain",
    "mixed": "mixed",
    "Open Chain": "open_chain",
    "Closed Chain": "closed_chain",
    "Mixed": "mixed",
}

GRIP_MAPPING = {
    "Overhand": "overhand",
    "Underhand": "underhand",
    "Neutral": "neutral",
    "Mixed": "mixed",
    "Hook": "hook",
    "overhand": "overhand",
    "underhand": "underhand",
    "neutral": "neutral",
    "mixed": "mixed",
    "hook": "hook",
}

DIFFICULTY_MAPPING = {
    "Novice": "novice",
    "Beginner": "beginner",
    "Intermediate": "intermediate",
    "Advanced": "advanced",
    "novice": "novice",
    "beginner": "beginner",
    "intermediate": "intermediate",
    "advanced": "advanced",
    "零基础": "novice",
    "初级": "beginner",
    "中级": "intermediate",
    "高级": "advanced",
}


@dataclass
class RelationshipStats:
    """关系统计"""
    total_exercises: int = 0
    exercises_with_attr: int = 0
    relationships_created: int = 0
    relationships_existing: int = 0
    errors: int = 0


class RelationshipBuilder:
    """关系构建器"""
    
    def __init__(self, neo4j_manager: Neo4jManager, data_source_path: str = None):
        """
        初始化关系构建器
        
        Args:
            neo4j_manager: Neo4j管理器实例
            data_source_path: 数据源文件路径
        """
        self.manager = neo4j_manager
        self.data_source_path = data_source_path or '/app/data/enhanced_perfect_exercises_dataset.json'
        self.exercise_data = {}
        
    def load_data_source(self) -> bool:
        """加载数据源"""
        try:
            logger.info(f"加载数据源: {self.data_source_path}")
            with open(self.data_source_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 处理数据格式
            if isinstance(data, dict) and 'enhanced_perfect_exercises' in data:
                exercises = data['enhanced_perfect_exercises']
            else:
                exercises = data
            
            # 建立ID索引
            for exercise in exercises:
                exercise_id = exercise.get('id')
                if exercise_id:
                    self.exercise_data[exercise_id] = exercise
            
            logger.info(f"✅ 加载了 {len(self.exercise_data)} 个动作数据")
            return True
            
        except Exception as e:
            logger.error(f"❌ 加载数据源失败: {str(e)}")
            return False
    
    def update_exercise_properties(self) -> Dict[str, int]:
        """更新Exercise节点的属性"""
        logger.info("\n" + "=" * 60)
        logger.info("更新Exercise节点属性")
        logger.info("=" * 60)
        
        stats = {"updated": 0, "skipped": 0, "errors": 0}
        
        for exercise_id, data in self.exercise_data.items():
            try:
                # 提取属性值
                force = FORCE_MAPPING.get(data.get('force_en', ''), '')
                mechanic = MECHANIC_MAPPING.get(data.get('mechanic_en', ''), '')
                kinetic_chain = KINETIC_CHAIN_MAPPING.get(data.get('kinetic_chain_type', ''), '')
                difficulty = DIFFICULTY_MAPPING.get(data.get('difficulty_en', ''), '')
                
                # 处理grips（可能是数组）
                grips_en = data.get('grips_en', []) or []
                grips = []
                for g in grips_en:
                    mapped = GRIP_MAPPING.get(g, '')
                    if mapped:
                        grips.append(mapped)
                
                # 更新Neo4j节点
                update_query = """
                MATCH (e:Exercise {id: $id})
                SET e.force = $force,
                    e.mechanic = $mechanic,
                    e.kinetic_chain = $kinetic_chain,
                    e.grips = $grips
                RETURN e.id as id
                """
                
                result = self.manager.execute_write(update_query, {
                    "id": exercise_id,
                    "force": force,
                    "mechanic": mechanic,
                    "kinetic_chain": kinetic_chain,
                    "grips": grips
                })
                
                if result:
                    stats["updated"] += 1
                else:
                    stats["skipped"] += 1
                    
            except Exception as e:
                logger.error(f"更新Exercise {exercise_id} 失败: {str(e)}")
                stats["errors"] += 1
        
        logger.info(f"  更新: {stats['updated']}, 跳过: {stats['skipped']}, 错误: {stats['errors']}")
        return stats
    
    def build_force_relationships(self) -> RelationshipStats:
        """构建USES_FORCE关系"""
        logger.info("\n构建 USES_FORCE 关系...")
        
        stats = RelationshipStats()
        
        # 获取Exercise总数
        count_query = "MATCH (e:Exercise) RETURN count(e) as total"
        result = self.manager.execute_query(count_query, {})
        stats.total_exercises = result[0]["total"] if result else 0
        
        # 获取有force属性的Exercise数量
        attr_query = """
        MATCH (e:Exercise)
        WHERE e.force IS NOT NULL AND e.force <> ''
        RETURN count(e) as count
        """
        result = self.manager.execute_query(attr_query, {})
        stats.exercises_with_attr = result[0]["count"] if result else 0
        
        # 构建关系
        build_query = """
        MATCH (e:Exercise), (f:ForceType)
        WHERE e.force IS NOT NULL AND e.force <> '' AND e.force = f.name
        MERGE (e)-[r:USES_FORCE]->(f)
        RETURN count(r) as created
        """
        
        result = self.manager.execute_write(build_query, {})
        stats.relationships_created = result[0]["created"] if result else 0
        
        logger.info(f"  ✅ USES_FORCE: {stats.relationships_created}/{stats.exercises_with_attr}")
        return stats
    
    def build_mechanic_relationships(self) -> RelationshipStats:
        """构建HAS_MECHANIC关系"""
        logger.info("\n构建 HAS_MECHANIC 关系...")
        
        stats = RelationshipStats()
        
        # 获取有mechanic属性的Exercise数量
        attr_query = """
        MATCH (e:Exercise)
        WHERE e.mechanic IS NOT NULL AND e.mechanic <> ''
        RETURN count(e) as count
        """
        result = self.manager.execute_query(attr_query, {})
        stats.exercises_with_attr = result[0]["count"] if result else 0
        
        # 构建关系
        build_query = """
        MATCH (e:Exercise), (m:MechanicType)
        WHERE e.mechanic IS NOT NULL AND e.mechanic <> '' AND e.mechanic = m.name
        MERGE (e)-[r:HAS_MECHANIC]->(m)
        RETURN count(r) as created
        """
        
        result = self.manager.execute_write(build_query, {})
        stats.relationships_created = result[0]["created"] if result else 0
        
        logger.info(f"  ✅ HAS_MECHANIC: {stats.relationships_created}/{stats.exercises_with_attr}")
        return stats
    
    def build_kinetic_chain_relationships(self) -> RelationshipStats:
        """构建HAS_KINETIC_CHAIN关系"""
        logger.info("\n构建 HAS_KINETIC_CHAIN 关系...")
        
        stats = RelationshipStats()
        
        # 获取有kinetic_chain属性的Exercise数量
        attr_query = """
        MATCH (e:Exercise)
        WHERE e.kinetic_chain IS NOT NULL AND e.kinetic_chain <> ''
        RETURN count(e) as count
        """
        result = self.manager.execute_query(attr_query, {})
        stats.exercises_with_attr = result[0]["count"] if result else 0
        
        # 构建关系
        build_query = """
        MATCH (e:Exercise), (k:KineticChain)
        WHERE e.kinetic_chain IS NOT NULL AND e.kinetic_chain <> '' AND e.kinetic_chain = k.name
        MERGE (e)-[r:HAS_KINETIC_CHAIN]->(k)
        RETURN count(r) as created
        """
        
        result = self.manager.execute_write(build_query, {})
        stats.relationships_created = result[0]["created"] if result else 0
        
        logger.info(f"  ✅ HAS_KINETIC_CHAIN: {stats.relationships_created}/{stats.exercises_with_attr}")
        return stats
    
    def build_grip_relationships(self) -> RelationshipStats:
        """构建USES_GRIP关系"""
        logger.info("\n构建 USES_GRIP 关系...")
        
        stats = RelationshipStats()
        
        # 获取有grips属性的Exercise数量
        attr_query = """
        MATCH (e:Exercise)
        WHERE e.grips IS NOT NULL AND size(e.grips) > 0
        RETURN count(e) as count
        """
        result = self.manager.execute_query(attr_query, {})
        stats.exercises_with_attr = result[0]["count"] if result else 0
        
        # 构建关系（处理数组）
        build_query = """
        MATCH (e:Exercise), (g:GripType)
        WHERE e.grips IS NOT NULL AND g.name IN e.grips
        MERGE (e)-[r:USES_GRIP]->(g)
        RETURN count(r) as created
        """
        
        result = self.manager.execute_write(build_query, {})
        stats.relationships_created = result[0]["created"] if result else 0
        
        logger.info(f"  ✅ USES_GRIP: {stats.relationships_created}/{stats.exercises_with_attr}")
        return stats
    
    def build_level_relationships(self) -> RelationshipStats:
        """构建SUITABLE_FOR_LEVEL关系"""
        logger.info("\n构建 SUITABLE_FOR_LEVEL 关系...")
        
        stats = RelationshipStats()
        
        # 获取有difficulty属性的Exercise数量
        attr_query = """
        MATCH (e:Exercise)
        WHERE e.difficulty IS NOT NULL AND e.difficulty <> ''
        RETURN count(e) as count
        """
        result = self.manager.execute_query(attr_query, {})
        stats.exercises_with_attr = result[0]["count"] if result else 0
        
        # 需要将中文difficulty映射到英文name
        # 先更新difficulty属性为英文
        mapping_queries = [
            ("零基础", "novice"),
            ("初级", "beginner"),
            ("中级", "intermediate"),
            ("高级", "advanced"),
        ]
        
        for zh, en in mapping_queries:
            update_query = f"""
            MATCH (e:Exercise)
            WHERE e.difficulty = '{zh}'
            SET e.difficulty_level = '{en}'
            """
            self.manager.execute_write(update_query, {})
        
        # 构建关系
        build_query = """
        MATCH (e:Exercise), (t:TrainingLevel)
        WHERE e.difficulty_level IS NOT NULL AND e.difficulty_level = t.name
        MERGE (e)-[r:SUITABLE_FOR_LEVEL]->(t)
        RETURN count(r) as created
        """
        
        result = self.manager.execute_write(build_query, {})
        stats.relationships_created = result[0]["created"] if result else 0
        
        logger.info(f"  ✅ SUITABLE_FOR_LEVEL: {stats.relationships_created}/{stats.exercises_with_attr}")
        return stats
    
    def build_all_relationships(self) -> Dict[str, RelationshipStats]:
        """构建所有关系"""
        logger.info("=" * 60)
        logger.info("开始构建Exercise关系")
        logger.info("=" * 60)
        
        results = {}
        
        # 1. 加载数据源
        if not self.load_data_source():
            return results
        
        # 2. 更新Exercise属性
        self.update_exercise_properties()
        
        # 3. 构建各类关系
        results["USES_FORCE"] = self.build_force_relationships()
        results["HAS_MECHANIC"] = self.build_mechanic_relationships()
        results["HAS_KINETIC_CHAIN"] = self.build_kinetic_chain_relationships()
        results["USES_GRIP"] = self.build_grip_relationships()
        results["SUITABLE_FOR_LEVEL"] = self.build_level_relationships()
        
        return results
    
    def get_coverage_stats(self) -> Dict[str, Any]:
        """获取关系覆盖率统计"""
        logger.info("\n" + "=" * 60)
        logger.info("关系覆盖率统计")
        logger.info("=" * 60)
        
        # 获取Exercise总数
        total_query = "MATCH (e:Exercise) RETURN count(e) as total"
        result = self.manager.execute_query(total_query, {})
        total_exercises = result[0]["total"] if result else 0
        
        stats = {"total_exercises": total_exercises, "relationships": {}}
        
        relationship_types = [
            ("USES_FORCE", "force"),
            ("HAS_MECHANIC", "mechanic"),
            ("HAS_KINETIC_CHAIN", "kinetic_chain"),
            ("USES_GRIP", "grips"),
            ("SUITABLE_FOR_LEVEL", "difficulty_level"),
        ]
        
        for rel_type, attr_name in relationship_types:
            # 统计有属性的Exercise
            if attr_name == "grips":
                attr_query = f"""
                MATCH (e:Exercise)
                WHERE e.{attr_name} IS NOT NULL AND size(e.{attr_name}) > 0
                RETURN count(e) as count
                """
            else:
                attr_query = f"""
                MATCH (e:Exercise)
                WHERE e.{attr_name} IS NOT NULL AND e.{attr_name} <> ''
                RETURN count(e) as count
                """
            
            attr_result = self.manager.execute_query(attr_query, {})
            exercises_with_attr = attr_result[0]["count"] if attr_result else 0
            
            # 统计有关系的Exercise
            rel_query = f"""
            MATCH (e:Exercise)-[:{rel_type}]->()
            RETURN count(DISTINCT e) as count
            """
            
            rel_result = self.manager.execute_query(rel_query, {})
            exercises_with_rel = rel_result[0]["count"] if rel_result else 0
            
            # 计算覆盖率
            coverage_rate = exercises_with_rel / exercises_with_attr if exercises_with_attr > 0 else 0.0
            
            stats["relationships"][rel_type] = {
                "exercises_with_attr": exercises_with_attr,
                "exercises_with_rel": exercises_with_rel,
                "coverage_rate": coverage_rate
            }
            
            status = "✅" if coverage_rate >= 0.9 else "⚠️"
            logger.info(f"  {status} {rel_type}: {exercises_with_rel}/{exercises_with_attr} ({coverage_rate:.1%})")
        
        # 计算总体覆盖率
        total_with_attr = sum(s["exercises_with_attr"] for s in stats["relationships"].values())
        total_with_rel = sum(s["exercises_with_rel"] for s in stats["relationships"].values())
        overall_rate = total_with_rel / total_with_attr if total_with_attr > 0 else 0.0
        
        stats["overall_coverage"] = overall_rate
        logger.info(f"\n  总体覆盖率: {overall_rate:.1%}")
        
        return stats


def main():
    """主函数"""
    # 从环境变量获取Neo4j配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    manager = None
    
    try:
        # 创建Neo4j管理器
        logger.info("连接Neo4j数据库...")
        manager = Neo4jManager(
            uri=neo4j_uri,
            user=neo4j_user,
            password=neo4j_password,
            database=neo4j_database
        )
        logger.info("✅ 数据库连接成功")
        
        # 创建关系构建器
        builder = RelationshipBuilder(manager)
        
        # 构建所有关系
        results = builder.build_all_relationships()
        
        # 获取覆盖率统计
        coverage = builder.get_coverage_stats()
        
        # 输出最终结果
        logger.info("\n" + "=" * 60)
        logger.info("构建完成")
        logger.info("=" * 60)
        
        if coverage.get("overall_coverage", 0) >= 0.9:
            logger.info("🎉 关系覆盖率达到90%目标！")
            return 0
        else:
            logger.warning(f"⚠️ 关系覆盖率 {coverage.get('overall_coverage', 0):.1%} 未达到90%目标")
            return 1
            
    except Exception as e:
        logger.error(f"❌ 执行失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        if manager:
            manager.close()
        logger.info("\n数据库连接已关闭")


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
