# -*- coding: utf-8 -*-
"""
修复剩余Muscle节点的name属性
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
    
    logger.info("修复剩余Muscle节点的name属性")
    logger.info("=" * 60)
    
    # 补充更多Muscle节点的英文名称
    muscles = {
        "大腿内侧": "inner_thigh",
        "股四头肌内侧": "vastus_medialis",
        "股四头肌外侧": "vastus_lateralis",
        "腹股沟": "groin",
        "上斜方肌": "upper_trapezius",
        "肩部": "shoulders",
        "下斜方肌": "lower_trapezius",
        "中斜方肌": "middle_trapezius",
        "下背部": "lower_back",
        "腿后肌群": "hamstrings",
        "腹肌": "abs",
        "核心肌群": "core_muscles",
        "小腿": "calves",
        "手臂": "arms",
        "胸部": "chest",
        "背部": "back",
        "腿部": "legs",
        "髋屈肌": "hip_flexors",
        "内收肌": "adductors",
        "外展肌": "abductors",
        "腰方肌": "quadratus_lumborum",
        "髂腰肌": "iliopsoas",
        "腹斜肌": "obliques",
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
    RETURN n.name_zh as name_zh
    """
    results = manager.execute_query(query, {})
    if results:
        missing = [r["name_zh"] for r in results]
        logger.warning(f"\n⚠️ 仍有 {len(missing)} 个Muscle节点缺少name属性:")
        for m in missing:
            logger.warning(f"  - {m}")
    else:
        logger.info("\n✅ 所有Muscle节点都有name属性")
    
    manager.close()
    logger.info("\n完成")


if __name__ == "__main__":
    main()
