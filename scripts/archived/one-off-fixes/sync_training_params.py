#!/usr/bin/env python3
"""
同步训练参数字段到Neo4j

补充以下字段：
- rep_range, set_range, rest_period, intensity_percentage
- safety_level, safety_pre_check, equipment_risks
- key_nutrients, recommended_foods, nutrition_timing
- description_zh, description_en (如果缺失)
"""
import json
from neo4j import GraphDatabase

NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"
DATASET_FILE = "/app/data/enhanced_perfect_exercises_dataset.json"

# 需要同步的训练参数字段
TRAINING_FIELDS = [
    'rep_range', 'set_range', 'rest_period', 'intensity_percentage',
    'safety_level', 'safety_pre_check', 'equipment_risks',
    'key_nutrients', 'recommended_foods', 'nutrition_timing',
    'description_zh', 'description_en'
]

def main():
    print("=" * 60)
    print("同步训练参数字段到Neo4j")
    print("=" * 60)
    
    # 加载数据集
    print(f"\n加载数据集: {DATASET_FILE}")
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    exercises = data.get('enhanced_perfect_exercises', [])
    print(f"数据集动作数量: {len(exercises)}")
    
    # 连接Neo4j
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    # 同步字段
    print(f"\n同步字段: {TRAINING_FIELDS}")
    updated = 0
    
    with driver.session() as session:
        for ex in exercises:
            ex_id = ex.get('id')
            if not ex_id:
                continue
            
            # 构建SET子句
            set_parts = []
            params = {'id': ex_id}
            
            for field in TRAINING_FIELDS:
                value = ex.get(field)
                if value is not None:
                    # 列表转JSON字符串（如果是复杂对象）
                    if isinstance(value, list) and value and isinstance(value[0], dict):
                        value = json.dumps(value, ensure_ascii=False)
                    params[field] = value
                    set_parts.append(f"e.{field} = ${field}")
            
            if set_parts:
                query = f"""
                    MATCH (e:Exercise {{id: $id}})
                    SET {', '.join(set_parts)}
                    RETURN e.id
                """
                result = session.run(query, **params)
                if result.single():
                    updated += 1
    
    print(f"更新了 {updated} 个节点")
    
    # 验证
    print("\n=== 验证结果 ===")
    with driver.session() as session:
        for field in ['rep_range', 'set_range', 'rest_period', 'intensity_percentage']:
            result = session.run(f'MATCH (e:Exercise) WHERE e.{field} IS NULL OR e.{field} = "" RETURN count(e) as cnt')
            cnt = result.single()['cnt']
            print(f"  {field} 空值: {cnt}")
        
        # 检查ID=12
        result = session.run("""
            MATCH (e:Exercise {id: 12})
            RETURN e.rep_range as rep, e.set_range as sets, e.rest_period as rest, e.intensity_percentage as intensity
        """)
        r = result.single()
        print(f"\nID=12 验证:")
        print(f"  rep_range: {r['rep']}")
        print(f"  set_range: {r['sets']}")
        print(f"  rest_period: {r['rest']}")
        print(f"  intensity_percentage: {r['intensity']}")
    
    driver.close()
    print("\n✅ 同步完成!")

if __name__ == "__main__":
    main()
