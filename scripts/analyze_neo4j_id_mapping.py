#!/usr/bin/env python3
"""
分析Neo4j与文件系统的ID映射关系

通过slug匹配建立Neo4j现有节点与文件系统动作的映射关系，
识别需要更新ID的现有节点和需要新增的动作。

Requirements:
- 2.1: 查询Neo4j获取现有Exercise节点 {slug: id}
- 2.2: 通过slug匹配建立映射
- 2.3: 识别新增动作（存在于FS但不在Neo4j中）

Usage:
    python scripts/analyze_neo4j_id_mapping.py
    
    # 在Docker容器中运行
    docker exec fitness_daml_rag python /app/../scripts/analyze_neo4j_id_mapping.py
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 路径配置
BASE_DIR = Path(__file__).parent.parent
LOG_DIR = BASE_DIR / "scripts" / "log"

# 增强数据集路径（包含文件系统的1790个动作）
ENHANCED_DATASET_PATHS = [
    BASE_DIR / "perfect_enhanced_dataset" / "data" / "enhanced_perfect_exercises_dataset.json",
    BASE_DIR / "daml-rag-server" / "data" / "enhanced_perfect_exercises_dataset.json",
    Path("/app/data/enhanced_perfect_exercises_dataset.json")  # Docker容器内路径
]

# Neo4j配置
NEO4J_CONFIG = {
    'uri': os.getenv('NEO4J_URI', 'bolt://fitness_neo4j:7687'),
    'user': os.getenv('NEO4J_USER', 'neo4j'),
    'password': os.getenv('NEO4J_PASSWORD', 'build_body_2024')
}


def get_neo4j_driver():
    """获取Neo4j驱动"""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            NEO4J_CONFIG['uri'],
            auth=(NEO4J_CONFIG['user'], NEO4J_CONFIG['password'])
        )
        # 测试连接
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info(f"✅ Neo4j连接成功: {NEO4J_CONFIG['uri']}")
        return driver
    except Exception as e:
        logger.error(f"❌ Neo4j连接失败: {e}")
        raise


def load_enhanced_dataset() -> List[Dict[str, Any]]:
    """加载增强数据集（文件系统的1790个动作）"""
    for path in ENHANCED_DATASET_PATHS:
        if path.exists():
            logger.info(f"📥 加载增强数据集: {path}")
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            exercises = data.get('enhanced_perfect_exercises', [])
            logger.info(f"✅ 加载了 {len(exercises)} 个动作")
            return exercises
    
    logger.error("❌ 未找到增强数据集文件")
    raise FileNotFoundError("增强数据集文件不存在")


def normalize_name_for_matching(name: str) -> str:
    """标准化名称用于匹配"""
    if not name:
        return ""
    # 转小写，移除特殊字符，空格替换为-
    normalized = name.lower()
    normalized = normalized.replace(' ', '-')
    normalized = normalized.replace('(', '').replace(')', '')
    normalized = normalized.replace("'", '').replace('"', '')
    normalized = normalized.replace(',', '').replace('.', '')
    return normalized


def query_neo4j_exercises(driver) -> Dict[str, Dict[str, Any]]:
    """
    查询Neo4j获取现有Exercise节点
    
    Returns:
        Dict[normalized_name_en, {id, name_zh, name_en}]
    """
    logger.info("🔍 查询Neo4j现有Exercise节点...")
    
    neo4j_exercises = {}
    
    with driver.session() as session:
        # 查询所有Exercise节点的id, name_zh, name_en
        # 注意：Neo4j中没有slug字段，使用name_en进行匹配
        result = session.run("""
            MATCH (e:Exercise)
            RETURN e.id as id, 
                   e.name_zh as name_zh, 
                   e.name_en as name_en
            ORDER BY e.id
        """)
        
        for record in result:
            exercise_id = record['id']
            name_zh = record['name_zh']
            name_en = record['name_en']
            
            # 使用标准化的name_en作为key
            if name_en:
                key = normalize_name_for_matching(name_en)
            else:
                # 使用id作为fallback
                key = f"id_{exercise_id}"
            
            neo4j_exercises[key] = {
                'id': exercise_id,
                'name_zh': name_zh,
                'name_en': name_en
            }
    
    logger.info(f"✅ Neo4j中有 {len(neo4j_exercises)} 个Exercise节点")
    return neo4j_exercises


def build_id_mapping(
    fs_exercises: List[Dict[str, Any]],
    neo4j_exercises: Dict[str, Dict[str, Any]]
) -> Tuple[Dict[str, Any], List[int], List[Dict[str, Any]]]:
    """
    通过name_en匹配建立ID映射
    
    Args:
        fs_exercises: 文件系统的动作列表（1790个）
        neo4j_exercises: Neo4j现有节点 {normalized_name_en: {id, name_zh, name_en}}
    
    Returns:
        Tuple[
            mapping: {neo4j_id: fs_id} 现有节点的ID映射,
            new_exercise_ids: 新增动作的ID列表,
            new_exercises: 新增动作的完整数据
        ]
    """
    logger.info("🔄 建立ID映射关系...")
    
    # 构建文件系统的多种匹配key
    fs_slug_map = {}  # {slug: exercise}
    fs_name_en_map = {}  # {normalized_name_en: exercise}
    
    for exercise in fs_exercises:
        slug = exercise.get('slug')
        name_en = exercise.get('name_en', '')
        
        if slug:
            fs_slug_map[slug] = exercise
        
        if name_en:
            # 标准化name_en
            normalized = normalize_name_for_matching(name_en)
            fs_name_en_map[normalized] = exercise
    
    # 建立映射
    id_mapping = {}  # {neo4j_id: fs_id}
    matched_fs_ids = set()  # 已匹配的文件系统ID
    unmatched_neo4j = []  # 未匹配的Neo4j节点
    
    for key, neo4j_data in neo4j_exercises.items():
        neo4j_id = neo4j_data['id']
        neo4j_name_en = neo4j_data.get('name_en', '')
        
        matched = False
        
        # 尝试通过标准化name_en匹配
        if key in fs_name_en_map:
            fs_exercise = fs_name_en_map[key]
            fs_id = fs_exercise['id']
            id_mapping[neo4j_id] = fs_id
            matched_fs_ids.add(fs_id)
            matched = True
        # 尝试通过slug匹配（如果key恰好是slug格式）
        elif key in fs_slug_map:
            fs_exercise = fs_slug_map[key]
            fs_id = fs_exercise['id']
            id_mapping[neo4j_id] = fs_id
            matched_fs_ids.add(fs_id)
            matched = True
        
        if not matched:
            unmatched_neo4j.append(neo4j_data)
    
    # 识别新增动作（存在于FS但未匹配到Neo4j）
    new_exercise_ids = []
    new_exercises = []
    
    for exercise in fs_exercises:
        fs_id = exercise['id']
        if fs_id not in matched_fs_ids:
            new_exercise_ids.append(fs_id)
            new_exercises.append(exercise)
    
    logger.info(f"✅ 映射完成:")
    logger.info(f"   - 已匹配节点: {len(id_mapping)}")
    logger.info(f"   - 新增动作: {len(new_exercise_ids)}")
    logger.info(f"   - 未匹配Neo4j节点: {len(unmatched_neo4j)}")
    
    return id_mapping, new_exercise_ids, new_exercises, unmatched_neo4j


def analyze_id_changes(id_mapping: Dict[int, int]) -> Dict[str, Any]:
    """分析ID变化情况"""
    unchanged = 0
    changed = 0
    changes = []
    
    for neo4j_id, fs_id in id_mapping.items():
        if neo4j_id == fs_id:
            unchanged += 1
        else:
            changed += 1
            changes.append({
                'neo4j_id': neo4j_id,
                'fs_id': fs_id,
                'change': fs_id - neo4j_id
            })
    
    return {
        'unchanged': unchanged,
        'changed': changed,
        'sample_changes': changes[:20]  # 只保存前20个示例
    }


def save_mapping_result(
    id_mapping: Dict[int, int],
    new_exercise_ids: List[int],
    new_exercises: List[Dict[str, Any]],
    unmatched_neo4j: List[Dict[str, Any]],
    neo4j_count: int,
    fs_count: int
) -> str:
    """保存映射结果到JSON文件"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    # 分析ID变化
    id_analysis = analyze_id_changes(id_mapping)
    
    # 构建slug到新ID的映射（用于后续更新）
    slug_to_new_id = {}
    for neo4j_id, fs_id in id_mapping.items():
        # 这里需要从原始数据中获取slug，暂时用id作为key
        slug_to_new_id[str(neo4j_id)] = fs_id
    
    result = {
        "report_title": "Neo4j ID映射分析报告",
        "generation_time": datetime.now().isoformat(),
        "statistics": {
            "neo4j_exercise_count": neo4j_count,
            "filesystem_exercise_count": fs_count,
            "mapped_count": len(id_mapping),
            "new_exercise_count": len(new_exercise_ids),
            "unmatched_neo4j_count": len(unmatched_neo4j)
        },
        "id_change_analysis": id_analysis,
        "id_mapping": {str(k): v for k, v in id_mapping.items()},  # neo4j_id -> fs_id
        "new_exercise_ids": sorted(new_exercise_ids),
        "new_exercises_summary": [
            {
                "id": e['id'],
                "slug": e.get('slug'),
                "name_zh": e.get('name_zh'),
                "name_en": e.get('name_en')
            }
            for e in new_exercises[:50]  # 只保存前50个摘要
        ],
        "unmatched_neo4j_nodes": unmatched_neo4j[:20],  # 只保存前20个
        "notes": [
            "id_mapping: Neo4j现有节点ID到文件系统ID的映射",
            "new_exercise_ids: 需要新增到Neo4j的动作ID列表",
            "这些ID是文件系统的原始跳跃ID"
        ]
    }
    
    output_file = LOG_DIR / "neo4j_id_mapping.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    logger.info(f"✅ 映射结果已保存到: {output_file}")
    return str(output_file)


def print_summary(
    neo4j_count: int,
    fs_count: int,
    mapped_count: int,
    new_count: int,
    unmatched_count: int,
    id_analysis: Dict[str, Any]
):
    """打印摘要信息"""
    print("\n" + "=" * 60)
    print("📊 Neo4j ID映射分析摘要")
    print("=" * 60)
    print(f"\n数据源统计:")
    print(f"  - Neo4j现有节点: {neo4j_count}")
    print(f"  - 文件系统动作: {fs_count}")
    
    print(f"\n映射结果:")
    print(f"  - 已匹配节点: {mapped_count}")
    print(f"  - 新增动作: {new_count}")
    print(f"  - 未匹配Neo4j节点: {unmatched_count}")
    
    print(f"\nID变化分析:")
    print(f"  - ID不变: {id_analysis['unchanged']}")
    print(f"  - ID需更新: {id_analysis['changed']}")
    
    if id_analysis['sample_changes']:
        print(f"\n  ID变化示例 (前5个):")
        for change in id_analysis['sample_changes'][:5]:
            print(f"    Neo4j ID {change['neo4j_id']} -> FS ID {change['fs_id']} (差值: {change['change']:+d})")
    
    print("\n" + "=" * 60)


def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("开始分析Neo4j与文件系统的ID映射关系")
    logger.info("=" * 60)
    
    try:
        # 1. 加载增强数据集（文件系统的1790个动作）
        logger.info("\n[1/4] 加载增强数据集...")
        fs_exercises = load_enhanced_dataset()
        
        # 2. 连接Neo4j并查询现有节点
        logger.info("\n[2/4] 查询Neo4j现有节点...")
        driver = get_neo4j_driver()
        neo4j_exercises = query_neo4j_exercises(driver)
        driver.close()
        
        # 3. 建立ID映射
        logger.info("\n[3/4] 建立ID映射...")
        id_mapping, new_exercise_ids, new_exercises, unmatched_neo4j = build_id_mapping(
            fs_exercises, neo4j_exercises
        )
        
        # 4. 保存结果
        logger.info("\n[4/4] 保存映射结果...")
        id_analysis = analyze_id_changes(id_mapping)
        output_file = save_mapping_result(
            id_mapping,
            new_exercise_ids,
            new_exercises,
            unmatched_neo4j,
            len(neo4j_exercises),
            len(fs_exercises)
        )
        
        # 打印摘要
        print_summary(
            len(neo4j_exercises),
            len(fs_exercises),
            len(id_mapping),
            len(new_exercise_ids),
            len(unmatched_neo4j),
            id_analysis
        )
        
        logger.info(f"\n✅ 分析完成! 结果保存在: {output_file}")
        return 0
        
    except Exception as e:
        logger.error(f"❌ 分析失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
