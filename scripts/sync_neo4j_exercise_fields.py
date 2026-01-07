#!/usr/bin/env python3
"""
同步Neo4j Exercise节点字段，补充缺失字段

从数据集补充以下字段：
- force_en, force_zh
- grips_en, grips_zh
- mechanic_en, mechanic_zh
- muscles_primary_en, muscles_primary_zh
- muscles_secondary_en, muscles_secondary_zh
- slug
- smart_tags
- variation_of, variations
- joints
"""
import json
from neo4j import GraphDatabase
from collections import Counter

# Neo4j配置
NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

# 数据集路径
DATASET_FILE = "/app/data/enhanced_perfect_exercises_dataset.json"

# 需要同步的字段
FIELDS_TO_SYNC = [
    'force_en', 'force_zh',
    'grips_en', 'grips_zh',
    'mechanic_en', 'mechanic_zh',
    'muscles_primary_en', 'muscles_primary_zh',
    'muscles_secondary_en', 'muscles_secondary_zh',
    'slug', 'smart_tags',
    'variation_of', 'variations',
    'joints'
]

# 需要删除的旧字段（已被新字段替代）
OLD_FIELDS_TO_REMOVE = [
    'force',      # 被 force_zh 替代
    'grips',      # 被 grips_zh 替代
    'mechanic',   # 被 mechanic_zh 替代
]

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def load_dataset():
    """加载数据集"""
    print(f"加载数据集: {DATASET_FILE}")
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    exercises = data.get('enhanced_perfect_exercises', [])
    print(f"数据集动作数量: {len(exercises)}")
    return {ex['id']: ex for ex in exercises if 'id' in ex}

def analyze_missing_fields(driver, dataset):
    """分析缺失字段"""
    print("\n=== 分析缺失字段 ===")
    
    with driver.session() as session:
        # 获取一个样本
        result = session.run("MATCH (e:Exercise) WHERE e.id = 12 RETURN e")
        record = result.single()
        if record:
            neo4j_fields = set(record['e'].keys())
            dataset_fields = set(dataset.get(12, {}).keys())
            
            missing = dataset_fields - neo4j_fields
            print(f"Neo4j缺少的字段: {sorted(missing)}")
            
            extra = neo4j_fields - dataset_fields
            print(f"Neo4j多余的字段: {sorted(extra)}")

def sync_fields(driver, dataset):
    """同步字段到Neo4j"""
    print(f"\n=== 同步字段到Neo4j ===")
    print(f"要同步的字段: {FIELDS_TO_SYNC}")
    
    updated = 0
    errors = 0
    
    with driver.session() as session:
        for ex_id, ex_data in dataset.items():
            try:
                # 构建SET子句
                set_parts = []
                params = {'id': ex_id}
                
                for field in FIELDS_TO_SYNC:
                    value = ex_data.get(field)
                    # 处理None值
                    if value is None:
                        value = None
                    # 处理列表（需要转为JSON字符串或保持列表）
                    elif isinstance(value, list):
                        # Neo4j支持列表，但复杂对象需要JSON
                        if value and isinstance(value[0], dict):
                            value = json.dumps(value, ensure_ascii=False)
                    
                    params[field] = value
                    set_parts.append(f"e.{field} = ${field}")
                
                # 执行更新
                query = f"""
                    MATCH (e:Exercise {{id: $id}})
                    SET {', '.join(set_parts)}
                    RETURN e.id
                """
                result = session.run(query, **params)
                if result.single():
                    updated += 1
                    
            except Exception as e:
                errors += 1
                if errors <= 3:
                    print(f"错误 ID={ex_id}: {e}")
    
    print(f"更新了 {updated} 个节点")
    if errors:
        print(f"错误数量: {errors}")

def remove_old_fields(driver):
    """删除旧字段"""
    print(f"\n=== 删除旧字段 ===")
    print(f"要删除的字段: {OLD_FIELDS_TO_REMOVE}")
    
    with driver.session() as session:
        for field in OLD_FIELDS_TO_REMOVE:
            result = session.run(f"""
                MATCH (e:Exercise)
                WHERE e.{field} IS NOT NULL
                REMOVE e.{field}
                RETURN count(e) as cnt
            """)
            count = result.single()['cnt']
            print(f"  删除 {field}: {count} 个节点")

def verify_results(driver):
    """验证结果"""
    print("\n=== 验证结果 ===")
    
    with driver.session() as session:
        # 检查字段是否存在
        result = session.run("MATCH (e:Exercise) WHERE e.id = 12 RETURN e")
        record = result.single()
        if record:
            node = record['e']
            print("ID=12 节点字段检查:")
            for field in FIELDS_TO_SYNC:
                value = node.get(field, '(不存在)')
                if isinstance(value, str) and len(value) > 50:
                    value = value[:50] + '...'
                print(f"  {field}: {value}")
        
        # 统计force_zh分布
        result = session.run("""
            MATCH (e:Exercise) 
            RETURN e.force_zh as val, count(*) as cnt 
            ORDER BY cnt DESC LIMIT 10
        """)
        print("\nforce_zh分布:")
        for r in result:
            print(f"  {r['val'] or '(空)'}: {r['cnt']}")
        
        # 统计mechanic_zh分布
        result = session.run("""
            MATCH (e:Exercise) 
            RETURN e.mechanic_zh as val, count(*) as cnt 
            ORDER BY cnt DESC LIMIT 10
        """)
        print("\nmechanic_zh分布:")
        for r in result:
            print(f"  {r['val'] or '(空)'}: {r['cnt']}")

def main():
    print("=" * 60)
    print("同步Neo4j Exercise节点字段")
    print("=" * 60)
    
    driver = get_driver()
    
    try:
        # 1. 加载数据集
        dataset = load_dataset()
        
        # 2. 分析缺失字段
        analyze_missing_fields(driver, dataset)
        
        # 3. 同步字段
        sync_fields(driver, dataset)
        
        # 4. 删除旧字段
        remove_old_fields(driver)
        
        # 5. 验证结果
        verify_results(driver)
        
        print("\n✅ 同步完成!")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()
