# -*- coding: utf-8 -*-
"""
修复剩余节点的双语属性

1. RehabilitationPhase节点添加name属性
2. Muscle节点添加name属性
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


def fix_rehabilitation_phase(manager: Neo4jManager):
    """修复RehabilitationPhase节点"""
    logger.info("\n修复RehabilitationPhase节点")
    logger.info("-" * 50)
    
    # RehabilitationPhase的英文名称映射
    phases = {
        "急性期": "acute",
        "亚急性期": "subacute",
        "恢复期": "recovery",
    }
    
    for name_zh, name in phases.items():
        update_query = """
        MATCH (n:RehabilitationPhase {name_zh: $name_zh})
        SET n.name = $name
        RETURN n.name as name, n.name_zh as name_zh
        """
        result = manager.execute_write(update_query, {"name_zh": name_zh, "name": name})
        if result:
            logger.info(f"  ✅ 已更新: {name_zh} -> {name}")


def fix_muscle_nodes(manager: Neo4jManager):
    """修复Muscle节点 - 添加英文name属性"""
    logger.info("\n修复Muscle节点")
    logger.info("-" * 50)
    
    # 常见肌肉的英文名称映射
    muscles = {
        "肱二头肌": "biceps",
        "肱二头肌长头": "biceps_long_head",
        "肱二头肌短头": "biceps_short_head",
        "肱三头肌": "triceps",
        "肱三头肌长头": "triceps_long_head",
        "肱三头肌外侧头": "triceps_lateral_head",
        "肱三头肌内侧头": "triceps_medial_head",
        "三角肌": "deltoid",
        "三角肌前束": "anterior_deltoid",
        "三角肌中束": "lateral_deltoid",
        "三角肌后束": "posterior_deltoid",
        "胸肌": "pectoralis",
        "胸大肌": "pectoralis_major",
        "上胸肌": "upper_chest",
        "中胸肌": "middle_chest",
        "下胸肌": "lower_chest",
        "中下胸肌": "mid_lower_chest",
        "背阔肌": "latissimus_dorsi",
        "斜方肌": "trapezius",
        "斜方肌上束": "upper_trapezius",
        "斜方肌中束": "middle_trapezius",
        "斜方肌下束": "lower_trapezius",
        "菱形肌": "rhomboids",
        "竖脊肌": "erector_spinae",
        "腹直肌": "rectus_abdominis",
        "腹外斜肌": "external_oblique",
        "腹内斜肌": "internal_oblique",
        "腹横肌": "transverse_abdominis",
        "股四头肌": "quadriceps",
        "股直肌": "rectus_femoris",
        "股外侧肌": "vastus_lateralis",
        "股内侧肌": "vastus_medialis",
        "股中间肌": "vastus_intermedius",
        "腘绳肌": "hamstrings",
        "股二头肌": "biceps_femoris",
        "半腱肌": "semitendinosus",
        "半膜肌": "semimembranosus",
        "臀大肌": "gluteus_maximus",
        "臀中肌": "gluteus_medius",
        "臀小肌": "gluteus_minimus",
        "臀部": "glutes",
        "小腿三头肌": "triceps_surae",
        "腓肠肌": "gastrocnemius",
        "比目鱼肌": "soleus",
        "前臂": "forearm",
        "前臂屈肌": "forearm_flexors",
        "前臂伸肌": "forearm_extensors",
        "肩前部": "front_shoulder",
        "肩后部": "rear_shoulder",
        "核心": "core",
    }
    
    updated = 0
    for name_zh, name in muscles.items():
        # 检查是否存在该节点
        check_query = """
        MATCH (n:Muscle {name_zh: $name_zh})
        WHERE n.name IS NULL OR n.name = ''
        RETURN n
        """
        result = manager.execute_query(check_query, {"name_zh": name_zh})
        
        if result:
            update_query = """
            MATCH (n:Muscle {name_zh: $name_zh})
            SET n.name = $name
            RETURN n.name as name, n.name_zh as name_zh
            """
            manager.execute_write(update_query, {"name_zh": name_zh, "name": name})
            logger.info(f"  ✅ 已更新: {name_zh} -> {name}")
            updated += 1
    
    logger.info(f"\n  共更新 {updated} 个Muscle节点")


def verify_results(manager: Neo4jManager):
    """验证修复结果"""
    logger.info("\n" + "=" * 60)
    logger.info("验证修复结果")
    logger.info("=" * 60)
    
    # 检查RehabilitationPhase
    query = "MATCH (n:RehabilitationPhase) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    logger.info(f"\nRehabilitationPhase节点 ({len(results)}个):")
    for r in results:
        name = r.get('name', 'None')
        name_zh = r.get('name_zh', 'None')
        status = "✅" if name and name_zh else "⚠️"
        logger.info(f"  {status} {name}: {name_zh}")
    
    # 检查Muscle节点（只显示缺少name的）
    query = """
    MATCH (n:Muscle)
    WHERE n.name IS NULL OR n.name = ''
    RETURN n.name_zh as name_zh
    LIMIT 10
    """
    results = manager.execute_query(query, {})
    if results:
        logger.info(f"\n⚠️ 仍有 Muscle节点缺少name属性:")
        for r in results:
            logger.info(f"  - {r.get('name_zh', 'None')}")
    else:
        logger.info("\n✅ 所有Muscle节点都有name属性")


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
    
    logger.info("=" * 60)
    logger.info("修复剩余节点的双语属性")
    logger.info("=" * 60)
    
    try:
        fix_rehabilitation_phase(manager)
        fix_muscle_nodes(manager)
        verify_results(manager)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 修复完成")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ 修复失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        manager.close()
    
    return 0


if __name__ == "__main__":
    exit(main())
