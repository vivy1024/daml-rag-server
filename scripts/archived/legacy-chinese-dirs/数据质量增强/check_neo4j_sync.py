#!/usr/bin/env python3
"""检查Neo4j数据库中的ROM数据同步状态"""

from neo4j import GraphDatabase
import json

# Neo4j连接配置
NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

def check_neo4j_rom_data():
    """检查Neo4j中的ROM数据"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    with driver.session() as session:
        # 检查总数
        result = session.run("MATCH (e:Exercise) RETURN count(e) as total")
        total = result.single()["total"]
        print(f"✅ Exercise节点总数: {total}")
        
        # 检查有ROM数据的节点数
        result = session.run("""
            MATCH (e:Exercise) 
            WHERE e.rom_requirements IS NOT NULL 
            RETURN count(e) as count
        """)
        rom_count = result.single()["count"]
        print(f"✅ 有ROM数据的节点数: {rom_count}")
        print(f"✅ 覆盖率: {rom_count/total*100:.1f}%")
        
        # 随机抽查3个节点的ROM数据
        result = session.run("""
            MATCH (e:Exercise) 
            WHERE e.rom_requirements IS NOT NULL 
            RETURN e.name_zh as name, e.rom_requirements as rom
            LIMIT 3
        """)
        
        print("\n随机抽查3个节点的ROM数据:")
        print("-" * 60)
        for record in result:
            name = record["name"]
            rom = record["rom"]
            print(f"\n动作: {name}")
            try:
                rom_data = json.loads(rom)
                print(f"ROM数据: {json.dumps(rom_data, ensure_ascii=False, indent=2)}")
            except:
                print(f"ROM数据: {rom}")
    
    driver.close()
    print("\n" + "=" * 60)
    print("✅ Neo4j数据库ROM数据同步验证完成")
    print("=" * 60)

if __name__ == "__main__":
    check_neo4j_rom_data()
