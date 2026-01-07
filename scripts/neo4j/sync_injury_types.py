# -*- coding: utf-8 -*-
"""
同步Neo4j InjuryType节点与前端选项

确保Neo4j中的InjuryType节点能够正确映射到前端的INJURY_HISTORY_OPTIONS

前端伤病选项 (yuzhen_fitness/src/types/user-profile.ts):
- 无、腰部损伤、膝盖损伤、肩部损伤、手腕损伤、脚踝损伤、颈部损伤、肘部损伤、髋部损伤、其他

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


# 前端伤病选项与Neo4j InjuryType的映射关系
# 每个前端选项对应多个具体的伤病类型
INJURY_TYPE_DEFINITIONS = {
    "腰部损伤": [
        {"name": "lower_back_pain", "name_zh": "下背部疼痛"},
        {"name": "herniated_disc", "name_zh": "腰椎间盘突出"},
    ],
    "膝盖损伤": [
        {"name": "acl_injury", "name_zh": "前交叉韧带损伤"},
        {"name": "knee_injury", "name_zh": "膝盖受伤"},
        {"name": "chondromalacia_patellae", "name_zh": "髌骨软化症"},
        {"name": "itbs", "name_zh": "髂胫束综合征"},
    ],
    "肩部损伤": [
        {"name": "shoulder_impingement", "name_zh": "肩峰撞击"},
        {"name": "rotator_cuff_injury", "name_zh": "肩袖损伤"},
        {"name": "shoulder_injury", "name_zh": "肩部受伤"},
    ],
    "手腕损伤": [
        {"name": "carpal_tunnel", "name_zh": "腕管综合征"},
        {"name": "wrist_injury", "name_zh": "腕部受伤"},
    ],
    "脚踝损伤": [
        {"name": "achilles_tendinitis", "name_zh": "跟腱炎"},
        {"name": "plantar_fasciitis", "name_zh": "足底筋膜炎"},
        {"name": "ankle_sprain", "name_zh": "踝关节扭伤"},
    ],
    "颈部损伤": [
        {"name": "cervical_spondylosis", "name_zh": "颈椎病"},
        {"name": "neck_injury", "name_zh": "颈部受伤"},
    ],
    "肘部损伤": [
        {"name": "tennis_elbow", "name_zh": "网球肘"},
        {"name": "golfers_elbow", "name_zh": "高尔夫球肘"},
    ],
    "髋部损伤": [
        {"name": "hip_impingement", "name_zh": "髋关节撞击"},
        {"name": "hip_bursitis", "name_zh": "髋滑囊炎"},
        {"name": "hip_injury", "name_zh": "髋部受伤"},
    ],
}


def sync_injury_types(manager: Neo4jManager):
    """同步InjuryType节点"""
    logger.info("=" * 70)
    logger.info("同步Neo4j InjuryType节点与前端选项")
    logger.info("=" * 70)
    
    # 1. 查看当前InjuryType节点
    logger.info("\n1. 当前InjuryType节点:")
    query = "MATCH (n:InjuryType) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name_zh"
    results = manager.execute_query(query, {})
    
    current_injuries = {}
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "")
        current_injuries[name] = name_zh
        logger.info(f"  - {name}: {name_zh}")
    
    logger.info(f"\n  共 {len(results)} 个InjuryType节点")
    
    # 2. 同步InjuryType节点
    logger.info("\n2. 同步InjuryType节点:")
    
    created = 0
    updated = 0
    
    for category, injuries in INJURY_TYPE_DEFINITIONS.items():
        logger.info(f"\n  [{category}]:")
        for injury in injuries:
            name = injury["name"]
            name_zh = injury["name_zh"]
            
            if name in current_injuries:
                # 更新现有节点
                if current_injuries[name] != name_zh:
                    update_query = """
                    MATCH (n:InjuryType {name: $name})
                    SET n.name_zh = $name_zh, n.category = $category
                    RETURN n.name as name, n.name_zh as name_zh
                    """
                    manager.execute_write(update_query, {
                        "name": name,
                        "name_zh": name_zh,
                        "category": category
                    })
                    logger.info(f"    ✅ 更新: {name_zh} ({name})")
                    updated += 1
                else:
                    # 只添加category属性
                    update_query = """
                    MATCH (n:InjuryType {name: $name})
                    SET n.category = $category
                    """
                    manager.execute_write(update_query, {
                        "name": name,
                        "category": category
                    })
                    logger.info(f"    ✓ 已存在: {name_zh} ({name})")
            else:
                # 创建新节点
                create_query = """
                CREATE (n:InjuryType {name: $name, name_zh: $name_zh, category: $category})
                RETURN n.name as name, n.name_zh as name_zh
                """
                manager.execute_write(create_query, {
                    "name": name,
                    "name_zh": name_zh,
                    "category": category
                })
                logger.info(f"    ✅ 创建: {name_zh} ({name})")
                created += 1
    
    logger.info(f"\n  创建: {created}, 更新: {updated}")
    
    # 3. 验证结果
    logger.info("\n3. 验证结果:")
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
        
        status = "✅" if name and name_zh else "⚠️"
        logger.info(f"    {status} {name_zh} ({name})")
    
    # 4. 检查前端选项覆盖率
    logger.info("\n4. 前端选项覆盖率检查:")
    for category in INJURY_TYPE_DEFINITIONS.keys():
        query = """
        MATCH (n:InjuryType {category: $category})
        RETURN count(n) as count
        """
        result = manager.execute_query(query, {"category": category})
        count = result[0]["count"] if result else 0
        expected = len(INJURY_TYPE_DEFINITIONS[category])
        status = "✅" if count >= expected else "⚠️"
        logger.info(f"  {status} {category}: {count}/{expected} 个伤病类型")


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
        sync_injury_types(manager)
        
        logger.info("\n" + "=" * 70)
        logger.info("✅ 同步完成")
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"❌ 同步失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        manager.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
