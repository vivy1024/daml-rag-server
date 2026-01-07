"""
统一Neo4j中Muscle节点的name_zh与Exercise.primary_muscle_zh

问题：
- Muscle节点的name_zh（如"胸肌"）与Exercise.primary_muscle_zh（如"胸部"）不一致
- 导致通过关系查询时无法正确匹配

解决方案：
- 以Exercise.primary_muscle_zh为准，更新Muscle节点的name_zh
- 保持数据一致性

作者: BUILD_BODY Team
日期: 2026-01-06
"""

import asyncio
import logging
from neo4j import GraphDatabase

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Neo4j连接配置
NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"


def get_exercise_muscle_names(session):
    """获取Exercise中使用的所有primary_muscle_zh值"""
    result = session.run("""
        MATCH (e:Exercise)
        WHERE e.primary_muscle_zh IS NOT NULL AND e.primary_muscle_zh <> ''
        RETURN DISTINCT e.primary_muscle_zh as muscle, count(e) as cnt
        ORDER BY cnt DESC
    """)
    return {r["muscle"]: r["cnt"] for r in result}


def get_muscle_node_names(session):
    """获取Muscle节点的所有name_zh值"""
    result = session.run("""
        MATCH (m:Muscle)
        RETURN m.name_zh as name, m.name_en as name_en, id(m) as node_id
    """)
    return {r["name"]: {"name_en": r["name_en"], "node_id": r["node_id"]} for r in result}


def analyze_mismatches(exercise_muscles, muscle_nodes):
    """分析不匹配的肌群名称"""
    exercise_set = set(exercise_muscles.keys())
    muscle_set = set(muscle_nodes.keys())
    
    # Exercise中有但Muscle节点中没有的
    missing_in_muscle = exercise_set - muscle_set
    # Muscle节点中有但Exercise中没有的
    unused_muscles = muscle_set - exercise_set
    # 两边都有的
    matched = exercise_set & muscle_set
    
    return {
        "missing_in_muscle": missing_in_muscle,
        "unused_muscles": unused_muscles,
        "matched": matched
    }


def create_missing_muscle_nodes(session, missing_muscles, exercise_muscles):
    """为Exercise中使用但Muscle节点中不存在的肌群创建新节点"""
    created = []
    for muscle_name in missing_muscles:
        count = exercise_muscles.get(muscle_name, 0)
        # 创建新的Muscle节点
        session.run("""
            CREATE (m:Muscle {
                name_zh: $name_zh,
                name_en: $name_zh,
                created_from: 'exercise_primary_muscle_zh',
                exercise_count: $count
            })
        """, name_zh=muscle_name, count=count)
        created.append(muscle_name)
        logger.info(f"✅ 创建Muscle节点: {muscle_name} ({count}个动作使用)")
    return created


def update_targets_relationships(session):
    """更新TARGETS_PRIMARY关系，确保Exercise与正确的Muscle节点关联"""
    # 先删除旧的关系
    session.run("""
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY]->(m:Muscle)
        DELETE r
    """)
    logger.info("🗑️ 已删除旧的TARGETS_PRIMARY关系")
    
    # 创建新的关系，基于Exercise.primary_muscle_zh
    result = session.run("""
        MATCH (e:Exercise), (m:Muscle)
        WHERE e.primary_muscle_zh = m.name_zh
        CREATE (e)-[:TARGETS_PRIMARY]->(m)
        RETURN count(*) as created
    """)
    created = result.single()["created"]
    logger.info(f"✅ 创建了 {created} 个新的TARGETS_PRIMARY关系")
    return created


def main():
    logger.info("=" * 60)
    logger.info("开始统一Neo4j肌群命名")
    logger.info("=" * 60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # 1. 获取当前数据
        logger.info("\n📊 步骤1: 分析当前数据...")
        exercise_muscles = get_exercise_muscle_names(session)
        muscle_nodes = get_muscle_node_names(session)
        
        logger.info(f"   Exercise.primary_muscle_zh: {len(exercise_muscles)} 种")
        logger.info(f"   Muscle节点: {len(muscle_nodes)} 个")
        
        # 2. 分析不匹配
        logger.info("\n📊 步骤2: 分析不匹配...")
        analysis = analyze_mismatches(exercise_muscles, muscle_nodes)
        
        logger.info(f"   ✅ 匹配: {len(analysis['matched'])} 个")
        logger.info(f"   ⚠️ Exercise中有但Muscle节点缺失: {len(analysis['missing_in_muscle'])} 个")
        logger.info(f"   ℹ️ Muscle节点存在但Exercise未使用: {len(analysis['unused_muscles'])} 个")
        
        if analysis['missing_in_muscle']:
            logger.info(f"\n   缺失的肌群: {sorted(analysis['missing_in_muscle'])}")
        
        # 3. 创建缺失的Muscle节点
        if analysis['missing_in_muscle']:
            logger.info("\n📊 步骤3: 创建缺失的Muscle节点...")
            created = create_missing_muscle_nodes(session, analysis['missing_in_muscle'], exercise_muscles)
            logger.info(f"   创建了 {len(created)} 个新节点")
        
        # 4. 更新TARGETS_PRIMARY关系
        logger.info("\n📊 步骤4: 更新TARGETS_PRIMARY关系...")
        update_targets_relationships(session)
        
        # 5. 验证结果
        logger.info("\n📊 步骤5: 验证结果...")
        result = session.run("""
            MATCH (e:Exercise)-[:TARGETS_PRIMARY]->(m:Muscle)
            RETURN count(DISTINCT e) as exercises_with_relation,
                   count(DISTINCT m) as muscles_with_relation
        """)
        stats = result.single()
        logger.info(f"   有TARGETS_PRIMARY关系的Exercise: {stats['exercises_with_relation']}")
        logger.info(f"   有TARGETS_PRIMARY关系的Muscle: {stats['muscles_with_relation']}")
        
        # 检查没有关系的Exercise
        result = session.run("""
            MATCH (e:Exercise)
            WHERE NOT (e)-[:TARGETS_PRIMARY]->(:Muscle)
              AND e.primary_muscle_zh IS NOT NULL 
              AND e.primary_muscle_zh <> ''
            RETURN count(e) as count
        """)
        no_relation = result.single()["count"]
        if no_relation > 0:
            logger.warning(f"   ⚠️ 仍有 {no_relation} 个Exercise没有TARGETS_PRIMARY关系")
        else:
            logger.info("   ✅ 所有有primary_muscle_zh的Exercise都有TARGETS_PRIMARY关系")
    
    driver.close()
    logger.info("\n" + "=" * 60)
    logger.info("✅ 肌群命名统一完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
