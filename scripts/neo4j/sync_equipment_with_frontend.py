# -*- coding: utf-8 -*-
"""
同步Neo4j Equipment节点与前端选项

1. 恢复被删除的Equipment节点（恢复、拉伸、有氧训练、瑜伽）
2. 统一所有Equipment节点名称为中文
3. 确保与前端EQUIPMENT_OPTIONS对应

前端器械选项 (yuzhen_fitness/src/types/user-profile.ts):
- 杠铃、哑铃、固定器械、自由重量架、史密斯架、龙门架、绳索、弹力带、壶铃、TRX、药球、波速球、健身球、跳箱、战绳、徒手

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


# 前端器械选项与Neo4j节点的映射
# name: 前端显示名称（中文）
# name_en: 英文名称（用于数据源匹配）
# aliases: 别名（用于模糊匹配）
EQUIPMENT_DEFINITIONS = [
    # 基础器械
    {"name": "杠铃", "name_en": "barbell", "aliases": ["杠铃", "barbell"]},
    {"name": "杠铃片", "name_en": "weight_plate", "aliases": ["杠铃片", "weight plate", "plates"]},
    {"name": "哑铃", "name_en": "dumbbell", "aliases": ["哑铃", "dumbbell", "dumbbells"]},
    {"name": "固定器械", "name_en": "machine", "aliases": ["器械", "固定器械", "machine", "machines"]},
    {"name": "史密斯架", "name_en": "smith_machine", "aliases": ["史密斯机", "史密斯架", "smith machine"]},
    {"name": "龙门架", "name_en": "cable_machine", "aliases": ["龙门架", "绳索训练", "cable", "cable machine"]},
    {"name": "绳索", "name_en": "cable", "aliases": ["绳索", "绳索训练", "cable"]},
    {"name": "弹力带", "name_en": "resistance_band", "aliases": ["弹力带", "阻力带", "resistance band", "bands"]},
    {"name": "壶铃", "name_en": "kettlebell", "aliases": ["壶铃", "kettlebell"]},
    
    # 功能性器械
    {"name": "TRX", "name_en": "trx", "aliases": ["TRX", "TRX悬挂训练", "suspension trainer"]},
    {"name": "药球", "name_en": "medicine_ball", "aliases": ["药球", "medicine ball"]},
    {"name": "波速球", "name_en": "bosu_ball", "aliases": ["波速球", "Bosu-Ball", "bosu ball", "bosu"]},
    {"name": "健身球", "name_en": "stability_ball", "aliases": ["健身球", "瑜伽球", "stability ball", "swiss ball"]},
    {"name": "跳箱", "name_en": "plyo_box", "aliases": ["跳箱", "plyo box", "box"]},
    {"name": "战绳", "name_en": "battle_rope", "aliases": ["战绳", "battle rope", "ropes"]},
    
    # 徒手/自重
    {"name": "徒手", "name_en": "bodyweight", "aliases": ["徒手", "徒手训练", "bodyweight", "自重"]},
    {"name": "自由重量架", "name_en": "free_weight_rack", "aliases": ["自由重量架", "power rack", "squat rack"]},
    
    # 训练类型（保留，前端分类用）
    {"name": "恢复", "name_en": "recovery", "aliases": ["恢复", "recovery"]},
    {"name": "拉伸", "name_en": "stretching", "aliases": ["拉伸", "stretching", "stretch"]},
    {"name": "有氧训练", "name_en": "cardio", "aliases": ["有氧训练", "有氧", "cardio"]},
    {"name": "瑜伽", "name_en": "yoga", "aliases": ["瑜伽", "yoga"]},
    
    # 其他特殊器械
    {"name": "Vitruvian", "name_en": "vitruvian", "aliases": ["Vitruvian", "Vitruvian智能训练器"]},
]


def sync_equipment_nodes(manager: Neo4jManager):
    """同步Equipment节点"""
    logger.info("=" * 70)
    logger.info("同步Neo4j Equipment节点与前端选项")
    logger.info("=" * 70)
    
    # 1. 查看当前Equipment节点
    logger.info("\n1. 当前Equipment节点:")
    query = "MATCH (n:Equipment) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name_zh"
    results = manager.execute_query(query, {})
    current_equipment = {}
    for r in results:
        name = r.get("name", "")
        name_zh = r.get("name_zh", "")
        current_equipment[name_zh or name] = {"name": name, "name_zh": name_zh}
        logger.info(f"  - {name}: {name_zh}")
    
    logger.info(f"\n  共 {len(results)} 个Equipment节点")
    
    # 2. 创建/更新Equipment节点
    logger.info("\n2. 同步Equipment节点:")
    
    created = 0
    updated = 0
    
    for equip in EQUIPMENT_DEFINITIONS:
        name_zh = equip["name"]
        name_en = equip["name_en"]
        
        # 检查是否存在（通过name_zh或别名）
        exists = False
        for alias in equip["aliases"]:
            if alias in current_equipment:
                exists = True
                break
        
        if exists:
            # 更新现有节点，确保name和name_zh都正确
            update_query = """
            MATCH (n:Equipment)
            WHERE n.name_zh IN $aliases OR n.name IN $aliases
            SET n.name = $name_en, n.name_zh = $name_zh
            RETURN n.name as name, n.name_zh as name_zh
            """
            result = manager.execute_write(update_query, {
                "aliases": equip["aliases"],
                "name_en": name_en,
                "name_zh": name_zh
            })
            if result:
                logger.info(f"  ✅ 更新: {name_zh} ({name_en})")
                updated += 1
        else:
            # 创建新节点
            create_query = """
            CREATE (n:Equipment {name: $name_en, name_zh: $name_zh})
            RETURN n.name as name, n.name_zh as name_zh
            """
            result = manager.execute_write(create_query, {
                "name_en": name_en,
                "name_zh": name_zh
            })
            if result:
                logger.info(f"  ✅ 创建: {name_zh} ({name_en})")
                created += 1
    
    logger.info(f"\n  创建: {created}, 更新: {updated}")
    
    # 3. 验证结果
    logger.info("\n3. 验证结果:")
    query = "MATCH (n:Equipment) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name_zh"
    results = manager.execute_query(query, {})
    
    logger.info(f"\n  Equipment节点 ({len(results)}个):")
    for r in results:
        name = r.get("name", "None")
        name_zh = r.get("name_zh", "None")
        status = "✅" if name and name_zh else "⚠️"
        logger.info(f"    {status} {name_zh} ({name})")


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
        sync_equipment_nodes(manager)
        
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
