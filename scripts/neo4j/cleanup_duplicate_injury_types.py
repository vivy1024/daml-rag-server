# -*- coding: utf-8 -*-
"""
清理重复的InjuryType节点

删除旧的中文name节点，保留新的英文name节点

版本: v1.0.0
日期: 2026-01-05
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


def cleanup_duplicate_injury_types(manager: Neo4jManager):
    """清理重复的InjuryType节点"""
    logger.info("=" * 70)
    logger.info("清理重复的InjuryType节点")
    logger.info("=" * 70)
    
    # 1. 查找没有category属性的旧节点（这些是需要删除的）
    logger.info("\n1. 查找旧的InjuryType节点（无category属性）:")
    query = """
    MATCH (n:InjuryType)
    WHERE n.category IS NULL
    RETURN n.name as name, n.name_zh as name_zh
    ORDER BY n.name_zh
    """
    results = manager.execute_query(query, {})
    
    old_nodes = []
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "")
        old_nodes.append(name)
        logger.info(f"  - {name}: {name_zh}")
    
    logger.info(f"\n  共 {len(old_nodes)} 个旧节点需要处理")
    
    if not old_nodes:
        logger.info("\n  没有需要清理的旧节点")
        return
    
    # 2. 迁移关系到新节点
    logger.info("\n2. 迁移关系到新节点:")
    
    # 定义旧节点到新节点的映射
    old_to_new_mapping = {
        "下背部疼痛": "lower_back_pain",
        "腰椎间盘突出": "herniated_disc",
        "前交叉韧带损伤": "acl_injury",
        "膝盖受伤": "knee_injury",
        "髌骨软化症": "chondromalacia_patellae",
        "髂胫束综合征": "itbs",
        "肩峰撞击": "shoulder_impingement",
        "肩袖损伤": "rotator_cuff_injury",
        "肩部受伤": "shoulder_injury",
        "腕管综合征": "carpal_tunnel",
        "腕部受伤": "wrist_injury",
        "跟腱炎": "achilles_tendinitis",
        "足底筋膜炎": "plantar_fasciitis",
        "颈椎病": "cervical_spondylosis",
        "颈部受伤": "neck_injury",
        "网球肘": "tennis_elbow",
        "高尔夫球肘": "golfers_elbow",
    }
    
    for old_name in old_nodes:
        new_name = old_to_new_mapping.get(old_name)
        if not new_name:
            logger.warning(f"  ⚠️ 未找到映射: {old_name}")
            continue
        
        # 检查是否有关系需要迁移
        check_query = """
        MATCH (old:InjuryType {name: $old_name})-[r]-()
        RETURN type(r) as rel_type, count(r) as count
        """
        rels = manager.execute_query(check_query, {"old_name": old_name})
        
        if rels:
            for rel in rels:
                rel_type = rel.get("rel_type")
                count = rel.get("count", 0)
                logger.info(f"  - {old_name}: {count} 个 {rel_type} 关系")
                
                # 迁移关系
                migrate_query = f"""
                MATCH (old:InjuryType {{name: $old_name}})-[r:{rel_type}]-(other)
                MATCH (new:InjuryType {{name: $new_name}})
                WHERE NOT (new)-[:{rel_type}]-(other)
                CREATE (new)-[:{rel_type}]->(other)
                """
                manager.execute_write(migrate_query, {
                    "old_name": old_name,
                    "new_name": new_name
                })
    
    # 3. 删除旧节点
    logger.info("\n3. 删除旧节点:")
    
    delete_query = """
    MATCH (n:InjuryType)
    WHERE n.category IS NULL
    DETACH DELETE n
    RETURN count(n) as deleted
    """
    result = manager.execute_write(delete_query, {})
    deleted = result[0]["deleted"] if result else 0
    logger.info(f"  ✅ 删除了 {deleted} 个旧节点")
    
    # 4. 验证结果
    logger.info("\n4. 验证结果:")
    query = """
    MATCH (n:InjuryType) 
    RETURN n.name as name, n.name_zh as name_zh, n.category as category 
    ORDER BY n.category, n.name_zh
    """
    results = manager.execute_query(query, {})
    
    logger.info(f"\n  InjuryType节点 ({len(results)}个):")
    current_category = None
    for r in results:
        name = r.get("name", "None")
        name_zh = r.get("name_zh", "None")
        category = r.get("category", "未分类")
        
        if category != current_category:
            current_category = category
            logger.info(f"\n  [{category}]:")
        
        logger.info(f"    ✅ {name_zh} ({name})")


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
    
    try:
        cleanup_duplicate_injury_types(manager)
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ 清理完成")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ 清理失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        manager.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
