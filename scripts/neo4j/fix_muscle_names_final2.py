# -*- coding: utf-8 -*-
"""
修复最后剩余的Muscle节点name属性
"""

import sys
import os
import logging

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    neo4j_database = os.getenv("NEO4J_DATABASE", "neo4j")
    
    manager = Neo4jManager(
        uri=neo4j_uri,
        user=neo4j_user,
        password=neo4j_password,
        database=neo4j_database
    )
    
    logger.info("修复最后剩余的Muscle节点name属性")
    logger.info("=" * 60)
    
    muscles = {
        "腿后肌群外侧": "lateral_hamstrings",
        "腿后肌群内侧": "medial_hamstrings",
        "腕屈肌": "wrist_flexors",
        "上腹肌": "upper_abs",
        "下腹肌": "lower_abs",
        "手部": "hands",
        "腕伸肌": "wrist_extensors",
        "胫骨前肌": "tibialis_anterior",
        "足部": "feet",
        "颈部": "neck",
    }
    
    updated = 0
    for name_zh, name in muscles.items():
        query = """
        MATCH (n:Muscle {name_zh: $name_zh})
        WHERE n.name IS NULL OR n.name = ''
        SET n.name = $name
        RETURN n.name as name, n.name_zh as name_zh
        """
        result = manager.execute_write(query, {"name_zh": name_zh, "name": name})
        if result:
            logger.info(f"  ✅ 已更新: {name_zh} -> {name}")
            updated += 1
    
    logger.info(f"\n共更新 {updated} 个Muscle节点")
    
    # 验证
    query = """
    MATCH (n:Muscle)
    WHERE n.name IS NULL OR n.name = ''
    RETURN count(n) as count
    """
    results = manager.execute_query(query, {})
    count = results[0]["count"] if results else 0
    
    if count > 0:
        logger.warning(f"\n⚠️ 仍有 {count} 个Muscle节点缺少name属性")
    else:
        logger.info("\n✅ 所有Muscle节点都有name属性")
    
    manager.close()
    logger.info("\n完成")


if __name__ == "__main__":
    main()
