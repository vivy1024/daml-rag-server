# -*- coding: utf-8 -*-
"""
修复InjuryType节点的中文名称

版本: v1.0.0
日期: 2026-01-05
Requirements: 3.3
"""

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.retrieval.graph.neo4j_manager import Neo4jManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# InjuryType中英文映射
INJURY_TYPE_MAPPING = {
    "膝盖受伤": "Knee Injury",
    "下背部疼痛": "Lower Back Pain",
    "肩部受伤": "Shoulder Injury",
    "腕部受伤": "Wrist Injury",
    "颈部受伤": "Neck Injury",
    "髋部受伤": "Hip Injury",
    "踝部受伤": "Ankle Injury",
    "肘部受伤": "Elbow Injury",
    "上背部疼痛": "Upper Back Pain",
    "腹股沟拉伤": "Groin Strain",
    "腿筋拉伤": "Hamstring Strain",
    "股四头肌拉伤": "Quadriceps Strain",
    "小腿拉伤": "Calf Strain",
    "足底筋膜炎": "Plantar Fasciitis",
    "网球肘": "Tennis Elbow",
    "高尔夫球肘": "Golfer's Elbow",
    "肩袖损伤": "Rotator Cuff Injury",
}

# 反向映射（英文到中文）
EN_TO_ZH_MAPPING = {v: k for k, v in INJURY_TYPE_MAPPING.items()}


def fix_injury_types():
    """修复InjuryType节点的中文名称"""
    manager = Neo4jManager(
        uri='bolt://neo4j:7687',
        user='neo4j',
        password='build_body_2024',
        database='neo4j'
    )
    
    try:
        logger.info("=" * 60)
        logger.info("修复InjuryType节点中文名称")
        logger.info("=" * 60)
        
        # 1. 查看当前状态
        query = '''
        MATCH (n:InjuryType)
        RETURN n.name as name, n.name_zh as name_zh
        ORDER BY n.name
        '''
        results = manager.execute_query(query, {})
        logger.info(f"当前InjuryType节点数: {len(results)}")
        
        missing_zh = []
        for r in results:
            name = r.get('name')
            name_zh = r.get('name_zh')
            if not name_zh:
                missing_zh.append(name)
                logger.info(f"  缺少中文名: {name}")
        
        if not missing_zh:
            logger.info("✅ 所有InjuryType节点都有中文名称")
            return True
        
        logger.info(f"\n需要修复 {len(missing_zh)} 个节点")
        
        # 2. 修复缺少中文名的节点
        fixed_count = 0
        for name in missing_zh:
            # 尝试从映射中获取中文名
            name_zh = None
            
            # 检查name是否是中文（已经是中文名但name_zh为空）
            if any('\u4e00' <= c <= '\u9fff' for c in name):
                # name本身是中文，直接使用
                name_zh = name
            else:
                # name是英文，从映射中获取中文
                name_zh = EN_TO_ZH_MAPPING.get(name)
            
            if name_zh:
                update_query = '''
                MATCH (n:InjuryType {name: $name})
                SET n.name_zh = $name_zh
                RETURN n
                '''
                manager.execute_write(update_query, {"name": name, "name_zh": name_zh})
                logger.info(f"  ✅ 修复: {name} -> {name_zh}")
                fixed_count += 1
            else:
                logger.warning(f"  ⚠️ 未找到映射: {name}")
        
        # 3. 验证结果
        logger.info("\n验证结果...")
        verify_query = '''
        MATCH (n:InjuryType)
        WHERE n.name_zh IS NULL OR n.name_zh = ''
        RETURN n.name as name
        '''
        remaining = manager.execute_query(verify_query, {})
        
        if not remaining:
            logger.info("🎉 所有InjuryType节点都有中文名称！")
            return True
        else:
            logger.warning(f"⚠️ 仍有 {len(remaining)} 个节点缺少中文名称")
            for r in remaining:
                logger.warning(f"  - {r.get('name')}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 修复失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        manager.close()


if __name__ == "__main__":
    success = fix_injury_types()
    sys.exit(0 if success else 1)
