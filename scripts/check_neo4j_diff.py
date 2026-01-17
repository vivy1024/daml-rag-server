#!/usr/bin/env python3
"""检查本地和生产Neo4j的差异"""
from neo4j import GraphDatabase

LOCAL_URI = "bolt://fitness_neo4j:7687"
PRODUCTION_URI = "bolt://182.92.78.183:32372"
AUTH = ("neo4j", "build_body_2024")

def get_relationship_counts(driver):
    """获取每种关系类型的数量"""
    with driver.session() as session:
        result = session.run("""
            MATCH ()-[r]->()
            RETURN type(r) as rel_type, count(r) as count
            ORDER BY count DESC
        """)
        return {record['rel_type']: record['count'] for record in result}

def main():
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=AUTH)
    prod_driver = GraphDatabase.driver(PRODUCTION_URI, auth=AUTH)
    
    try:
        print("=" * 60)
        print("Neo4j关系类型对比")
        print("=" * 60)
        
        local_rels = get_relationship_counts(local_driver)
        prod_rels = get_relationship_counts(prod_driver)
        
        all_types = set(local_rels.keys()) | set(prod_rels.keys())
        
        print(f"\n{'关系类型':<30} {'本地':<10} {'生产':<10} {'差异':<10}")
        print("-" * 60)
        
        total_diff = 0
        for rel_type in sorted(all_types):
            local_count = local_rels.get(rel_type, 0)
            prod_count = prod_rels.get(rel_type, 0)
            diff = local_count - prod_count
            total_diff += diff
            
            status = "✅" if diff == 0 else "⚠️"
            print(f"{status} {rel_type:<28} {local_count:<10} {prod_count:<10} {diff:<10}")
        
        print("-" * 60)
        print(f"{'总计':<30} {sum(local_rels.values()):<10} {sum(prod_rels.values()):<10} {total_diff:<10}")
        
    finally:
        local_driver.close()
        prod_driver.close()

if __name__ == "__main__":
    main()
