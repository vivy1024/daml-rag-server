# -*- coding: utf-8 -*-
"""
修复Equipment节点的双语属性

为缺少中文名称的Equipment节点添加name_zh
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
    
    logger.info("修复Equipment节点双语属性")
    logger.info("=" * 60)
    
    # 需要添加中文名称的Equipment
    equipment_zh = {
        "TRX": "TRX悬挂训练",
        "Bosu-Ball": "波速球",
        "Vitruvian": "Vitruvian智能训练器",
    }
    
    for name, name_zh in equipment_zh.items():
        update_query = """
        MATCH (n:Equipment {name: $name})
        SET n.name_zh = $name_zh
        RETURN n.name as name, n.name_zh as name_zh
        """
        result = manager.execute_write(update_query, {"name": name, "name_zh": name_zh})
        if result:
            logger.info(f"  ✅ 已更新: {name} -> {name_zh}")
        else:
            logger.info(f"  ℹ️ 未找到: {name}")
    
    # 验证结果
    logger.info("\n验证结果:")
    query = "MATCH (n:Equipment) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    
    for r in results:
        name = r.get('name', 'None')
        name_zh = r.get('name_zh', 'None')
        status = "✅" if name and name_zh else "⚠️"
        logger.info(f"  {status} {name}: {name_zh}")
    
    manager.close()
    logger.info("\n✅ 完成")


if __name__ == "__main__":
    main()
