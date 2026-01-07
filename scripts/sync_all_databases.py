#!/usr/bin/env python3
"""
同步数据集到Neo4j和Qdrant
包含description_zh, force_zh, mechanic_zh, grips_zh等字段
"""
import json
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from sentence_transformers import SentenceTransformer

# 配置
NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"
QDRANT_HOST = "fitness_qdrant"
QDRANT_PORT = 6333
DATASET_FILE = "/app/data/enhanced_perfect_exercises_dataset.json"

# 需要同步的字段
FIELDS_TO_SYNC = [
    'description_zh', 'description_en',
    'force_en', 'force_zh',
    'grips_en', 'grips_zh',
    'mechanic_en', 'mechanic_zh',
]

def load_dataset():
    """加载数据集"""
    print(f"加载数据集: {DATASET_FILE}")
    with open(DATASET_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    exercises = data.get('enhanced_perfect_exercises', [])
    print(f"数据集动作数量: {len(exercises)}")
    return {ex['id']: ex for ex in exercises if 'id' in ex}

def sync_neo4j(dataset):
    """同步到Neo4j"""
    print("\n" + "=" * 60)
    print("同步到Neo4j")
    print("=" * 60)
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    updated = 0
    
    try:
        with driver.session() as session:
            for ex_id, ex_data in dataset.items():
                # 构建SET子句
                set_parts = []
                params = {'id': ex_id}
                
                for field in FIELDS_TO_SYNC:
                    value = ex_data.get(field)
                    if isinstance(value, list):
                        if value and isinstance(value[0], dict):
                            value = json.dumps(value, ensure_ascii=False)
                    params[field] = value
                    set_parts.append(f"e.{field} = ${field}")
                
                query = f"""
                    MATCH (e:Exercise {{id: $id}})
                    SET {', '.join(set_parts)}
                    RETURN e.id
                """
                result = session.run(query, **params)
                if result.single():
                    updated += 1
        
        print(f"✅ Neo4j更新了 {updated} 个节点")
        
        # 验证
        with driver.session() as session:
            result = session.run("""
                MATCH (e:Exercise) 
                WHERE e.description_zh IS NOT NULL AND e.description_zh <> ''
                RETURN count(e) as cnt
            """)
            cnt = result.single()['cnt']
            print(f"   有description_zh的节点: {cnt}")
            
    finally:
        driver.close()

def sync_qdrant(dataset):
    """同步到Qdrant"""
    print("\n" + "=" * 60)
    print("同步到Qdrant")
    print("=" * 60)
    
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # 获取现有点
    collection_name = "fitness_exercises_v2"
    
    # 批量更新payload
    updated = 0
    batch_size = 100
    ids = list(dataset.keys())
    
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        
        for ex_id in batch_ids:
            ex_data = dataset[ex_id]
            payload_update = {}
            
            for field in FIELDS_TO_SYNC:
                value = ex_data.get(field)
                if value is not None:
                    payload_update[field] = value
            
            if payload_update:
                try:
                    client.set_payload(
                        collection_name=collection_name,
                        payload=payload_update,
                        points=[ex_id]
                    )
                    updated += 1
                except Exception as e:
                    pass  # 点可能不存在
    
    print(f"✅ Qdrant更新了 {updated} 个向量")
    
    # 验证
    result = client.scroll(
        collection_name=collection_name,
        limit=10,
        with_payload=True
    )
    
    has_desc = 0
    for point in result[0]:
        if point.payload.get('description_zh'):
            has_desc += 1
    print(f"   前10个中有description_zh的: {has_desc}")

def main():
    print("=" * 60)
    print("同步数据集到Neo4j和Qdrant")
    print("=" * 60)
    
    # 1. 加载数据集
    dataset = load_dataset()
    
    # 2. 同步到Neo4j
    sync_neo4j(dataset)
    
    # 3. 同步到Qdrant
    sync_qdrant(dataset)
    
    print("\n" + "=" * 60)
    print("✅ 全部同步完成!")
    print("=" * 60)

if __name__ == "__main__":
    main()
