# -*- coding: utf-8 -*-
"""
修复和统一TrainingLevel节点

统一标准（简化为4级）：
- novice: 零基础 (0-3个月，完全没有训练经验)
- beginner: 初级 (3-12个月训练经验)
- intermediate: 中级 (1-3年训练经验)
- advanced: 高级 (3年以上训练经验)

版本: v1.2.0
日期: 2026-01-05
"""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 统一的训练等级标准（简化为4级）
TRAINING_LEVELS = [
    {"name": "novice", "name_zh": "零基础", "name_en": "Novice", "order": 1, "description": "0-3个月，完全没有训练经验"},
    {"name": "beginner", "name_zh": "初级", "name_en": "Beginner", "order": 2, "description": "3-12个月训练经验"},
    {"name": "intermediate", "name_zh": "中级", "name_en": "Intermediate", "order": 3, "description": "1-3年训练经验"},
    {"name": "advanced", "name_zh": "高级", "name_en": "Advanced", "order": 4, "description": "3年以上训练经验"},
]

# 中文到英文的映射
ZH_TO_EN_MAP = {
    "零基础": "novice",
    "初级": "beginner",
    "初学者": "beginner",  # 兼容旧数据
    "新手": "novice",      # 兼容旧数据
    "中级": "intermediate",
    "高级": "advanced",
}


def fix_training_levels():
    """修复TrainingLevel节点"""
    manager = Neo4jManager(
        uri='bolt://neo4j:7687',
        user='neo4j',
        password='build_body_2024',
        database='neo4j'
    )
    
    try:
        logger.info("=" * 60)
        logger.info("开始修复TrainingLevel节点")
        logger.info("=" * 60)
        
        # 1. 查看当前状态
        query = '''
        MATCH (n:TrainingLevel)
        RETURN n.name as name, n.name_zh as name_zh, n.name_en as name_en
        ORDER BY n.name
        '''
        results = manager.execute_query(query, {})
        logger.info(f"当前TrainingLevel节点数: {len(results)}")
        for r in results:
            logger.info(f"  name={r.get('name')}, name_zh={r.get('name_zh')}, name_en={r.get('name_en')}")
        
        # 2. 删除所有旧的TrainingLevel节点
        logger.info("\n删除所有旧的TrainingLevel节点...")
        delete_query = '''
        MATCH (n:TrainingLevel)
        DETACH DELETE n
        RETURN count(n) as deleted
        '''
        result = manager.execute_write(delete_query, {})
        deleted = result[0]['deleted'] if result else 0
        logger.info(f"  删除了 {deleted} 个节点")
        
        # 3. 创建新的标准化节点
        logger.info("\n创建标准化TrainingLevel节点...")
        for level in TRAINING_LEVELS:
            create_query = '''
            CREATE (n:TrainingLevel {
                name: $name,
                name_zh: $name_zh,
                name_en: $name_en,
                order: $order,
                description: $description
            })
            RETURN n
            '''
            manager.execute_write(create_query, level)
            logger.info(f"  ✅ 创建: {level['name']} ({level['name_zh']})")
        
        # 4. 验证结果
        logger.info("\n验证结果...")
        verify_query = '''
        MATCH (n:TrainingLevel)
        RETURN n.name as name, n.name_zh as name_zh, n.name_en as name_en, n.order as order
        ORDER BY n.order
        '''
        results = manager.execute_query(verify_query, {})
        logger.info(f"当前TrainingLevel节点数: {len(results)}")
        for r in results:
            logger.info(f"  {r.get('order')}. {r.get('name')} ({r.get('name_zh')}) - {r.get('name_en')}")
        
        # 5. 检查Exercise的difficulty分布
        logger.info("\n检查Exercise difficulty分布...")
        diff_query = '''
        MATCH (e:Exercise)
        RETURN e.difficulty as difficulty, count(e) as count
        ORDER BY count DESC
        '''
        diff_results = manager.execute_query(diff_query, {})
        for r in diff_results:
            logger.info(f"  {r.get('difficulty')}: {r.get('count')}个")
        
        logger.info("\n" + "=" * 60)
        logger.info("🎉 TrainingLevel节点修复完成！")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ 修复失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        manager.close()


if __name__ == "__main__":
    success = fix_training_levels()
    sys.exit(0 if success else 1)
