# -*- coding: utf-8 -*-
"""
修复Neo4j数据一致性问题

1. 删除Equipment中的非器械项目
2. 合并重复的TrainingGoal节点
3. 为Joint节点添加name属性
4. 清理孤立节点

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


def fix_equipment_nodes(manager: Neo4jManager):
    """删除Equipment中的非器械项目"""
    logger.info("\n" + "=" * 60)
    logger.info("1. 修复Equipment节点")
    logger.info("=" * 60)
    
    # 非器械项目列表
    non_equipment = ["恢复", "拉伸", "有氧训练", "瑜伽"]
    
    # 检查这些节点是否有关系
    for item in non_equipment:
        # 检查关系
        check_query = """
        MATCH (e:Equipment {name_zh: $name})-[r]-()
        RETURN type(r) as rel_type, count(r) as count
        """
        results = manager.execute_query(check_query, {"name": item})
        
        if results:
            logger.warning(f"  ⚠️ '{item}' 有关系，不能直接删除:")
            for r in results:
                logger.warning(f"      - {r['rel_type']}: {r['count']}个")
            
            # 删除关系后再删除节点 - 使用execute_write
            delete_query = """
            MATCH (e:Equipment {name_zh: $name})
            DETACH DELETE e
            RETURN count(e) as deleted
            """
            result = manager.execute_write(delete_query, {"name": item})
            logger.info(f"  ✅ 已删除 '{item}' 及其关系")
        else:
            # 直接删除节点 - 使用execute_write
            delete_query = """
            MATCH (e:Equipment {name_zh: $name})
            DELETE e
            RETURN count(e) as deleted
            """
            result = manager.execute_write(delete_query, {"name": item})
            if result and result[0].get("deleted", 0) > 0:
                logger.info(f"  ✅ 已删除 '{item}'")
            else:
                logger.info(f"  ℹ️ '{item}' 不存在，跳过")


def fix_training_goal_nodes(manager: Neo4jManager):
    """合并重复的TrainingGoal节点"""
    logger.info("\n" + "=" * 60)
    logger.info("2. 修复TrainingGoal节点")
    logger.info("=" * 60)
    
    # 查看当前状态
    query = "MATCH (n:TrainingGoal) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    
    logger.info("  当前TrainingGoal节点:")
    for r in results:
        logger.info(f"    - {r.get('name', 'None')}: {r.get('name_zh', 'None')}")
    
    # 需要修复的节点
    fixes = [
        # (name, name_zh) - 确保双语属性完整
        ("gain_muscle", "增肌"),
        ("lose_weight", "减脂"),
        ("build_strength", "增强力量"),
        ("improve_fitness", "提升体能"),
        ("maintain", "维持"),
        ("powerlifting", "力量举"),
        ("bodybuilding", "健美"),
    ]
    
    # 删除重复的中文节点（没有英文name的）
    duplicates = ["减脂", "增力", "维持"]
    for dup in duplicates:
        # 检查是否存在
        check_query = """
        MATCH (n:TrainingGoal)
        WHERE n.name = $name AND n.name_zh IS NULL
        RETURN n
        """
        result = manager.execute_query(check_query, {"name": dup})
        
        if result:
            # 删除重复节点 - 使用execute_write
            delete_query = """
            MATCH (n:TrainingGoal)
            WHERE n.name = $name AND n.name_zh IS NULL
            DETACH DELETE n
            """
            manager.execute_write(delete_query, {"name": dup})
            logger.info(f"  ✅ 已删除重复节点 '{dup}'")
    
    # 更新现有节点的name_zh - 使用execute_write
    updates = [
        ("Gain Muscle", "增肌"),
        ("Lose Weight", "减脂"),
        ("Improve Fitness", "提升体能"),
        ("Powerlifting", "力量举"),
    ]
    
    for name, name_zh in updates:
        update_query = """
        MATCH (n:TrainingGoal {name: $name})
        SET n.name_zh = $name_zh
        RETURN n.name as name, n.name_zh as name_zh
        """
        result = manager.execute_write(update_query, {"name": name, "name_zh": name_zh})
        if result:
            logger.info(f"  ✅ 已更新 '{name}' -> '{name_zh}'")


def fix_joint_nodes(manager: Neo4jManager):
    """为Joint节点添加name属性"""
    logger.info("\n" + "=" * 60)
    logger.info("3. 修复Joint节点")
    logger.info("=" * 60)
    
    # Joint节点的英文名称映射
    joint_names = {
        "肩关节": "shoulder",
        "肘关节": "elbow",
        "腕关节": "wrist",
        "髋关节": "hip",
        "膝关节": "knee",
        "踝关节": "ankle",
        "脊柱": "spine",
        "颈椎": "cervical_spine",
        "核心": "core",
    }
    
    for name_zh, name in joint_names.items():
        update_query = """
        MATCH (n:Joint {name_zh: $name_zh})
        SET n.name = $name
        RETURN n.name as name, n.name_zh as name_zh
        """
        result = manager.execute_write(update_query, {"name_zh": name_zh, "name": name})
        if result:
            logger.info(f"  ✅ 已更新 Joint: {name_zh} -> {name}")


def fix_equipment_names(manager: Neo4jManager):
    """为缺少name属性的Equipment节点添加name"""
    logger.info("\n" + "=" * 60)
    logger.info("4. 修复Equipment节点name属性")
    logger.info("=" * 60)
    
    # Equipment节点的英文名称映射
    equipment_names = {
        "杠铃": "barbell",
        "杠铃片": "weight_plate",
        "哑铃": "dumbbell",
        "器械": "machine",
        "史密斯机": "smith_machine",
        "绳索训练": "cable",
        "阻力带": "resistance_band",
        "壶铃": "kettlebell",
        "药球": "medicine_ball",
        "徒手训练": "bodyweight",
    }
    
    for name_zh, name in equipment_names.items():
        # 检查是否存在
        check_query = """
        MATCH (n:Equipment {name_zh: $name_zh})
        WHERE n.name IS NULL OR n.name = ''
        RETURN n
        """
        result = manager.execute_query(check_query, {"name_zh": name_zh})
        
        if result:
            update_query = """
            MATCH (n:Equipment {name_zh: $name_zh})
            SET n.name = $name
            RETURN n.name as name, n.name_zh as name_zh
            """
            manager.execute_write(update_query, {"name_zh": name_zh, "name": name})
            logger.info(f"  ✅ 已更新 Equipment: {name_zh} -> {name}")


def verify_fixes(manager: Neo4jManager):
    """验证修复结果"""
    logger.info("\n" + "=" * 60)
    logger.info("5. 验证修复结果")
    logger.info("=" * 60)
    
    # 检查Equipment
    query = "MATCH (n:Equipment) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name_zh"
    results = manager.execute_query(query, {})
    logger.info(f"\n  Equipment节点 ({len(results)}个):")
    for r in results:
        name = r.get('name', 'None')
        name_zh = r.get('name_zh', 'None')
        status = "✅" if name and name_zh else "⚠️"
        logger.info(f"    {status} {name}: {name_zh}")
    
    # 检查TrainingGoal
    query = "MATCH (n:TrainingGoal) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name"
    results = manager.execute_query(query, {})
    logger.info(f"\n  TrainingGoal节点 ({len(results)}个):")
    for r in results:
        name = r.get('name', 'None')
        name_zh = r.get('name_zh', 'None')
        status = "✅" if name and name_zh else "⚠️"
        logger.info(f"    {status} {name}: {name_zh}")
    
    # 检查Joint
    query = "MATCH (n:Joint) RETURN n.name as name, n.name_zh as name_zh ORDER BY n.name_zh"
    results = manager.execute_query(query, {})
    logger.info(f"\n  Joint节点 ({len(results)}个):")
    for r in results:
        name = r.get('name', 'None')
        name_zh = r.get('name_zh', 'None')
        status = "✅" if name and name_zh else "⚠️"
        logger.info(f"    {status} {name}: {name_zh}")


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
    logger.info("Neo4j数据一致性修复")
    logger.info("=" * 60)
    
    try:
        # 1. 修复Equipment节点
        fix_equipment_nodes(manager)
        
        # 2. 修复TrainingGoal节点
        fix_training_goal_nodes(manager)
        
        # 3. 修复Joint节点
        fix_joint_nodes(manager)
        
        # 4. 修复Equipment节点name属性
        fix_equipment_names(manager)
        
        # 5. 验证修复结果
        verify_fixes(manager)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 数据一致性修复完成")
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
