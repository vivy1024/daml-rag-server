"""
清理和统一Muscle节点

问题：
- Exercise.primary_muscle_zh有40种不同的值
- Neo4j有62个Muscle节点，存在22个冗余节点
- 需要删除未被Exercise使用的Muscle节点

策略：
1. 以Exercise.primary_muscle_zh为唯一标准
2. 删除未被任何Exercise使用的Muscle节点
3. 保留有TARGETS_PRIMARY关系的节点

作者: BUILD_BODY Team
日期: 2026-01-06
"""

from neo4j import GraphDatabase

NEO4J_URI = "bolt://neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

print("=" * 70)
print("清理Muscle节点 - 以Exercise.primary_muscle_zh为标准")
print("=" * 70)

with driver.session() as session:
    # 1. 获取Exercise中实际使用的肌群名称
    print("\n📊 步骤1: 获取Exercise中实际使用的肌群名称")
    result = session.run("""
        MATCH (e:Exercise)
        WHERE e.primary_muscle_zh IS NOT NULL AND e.primary_muscle_zh <> ''
        RETURN DISTINCT e.primary_muscle_zh as muscle, count(e) as cnt
        ORDER BY cnt DESC
    """)
    exercise_muscles = {r["muscle"]: r["cnt"] for r in result}
    print(f"   Exercise中使用的肌群: {len(exercise_muscles)} 种")
    
    # 2. 获取当前所有Muscle节点
    print("\n📊 步骤2: 获取当前Muscle节点")
    result = session.run("""
        MATCH (m:Muscle)
        RETURN m.name_zh as name
        ORDER BY name
    """)
    muscle_nodes = [r["name"] for r in result]
    print(f"   当前Muscle节点: {len(muscle_nodes)} 个")
    
    # 3. 找出未被使用的Muscle节点
    print("\n📊 步骤3: 分析未被使用的Muscle节点")
    exercise_set = set(exercise_muscles.keys())
    muscle_set = set(muscle_nodes)
    
    unused_muscles = muscle_set - exercise_set
    print(f"   未被Exercise使用的Muscle节点: {len(unused_muscles)} 个")
    for m in sorted(unused_muscles):
        print(f"      - {m}")
    
    # 4. 删除未被使用的Muscle节点
    if unused_muscles:
        print(f"\n📊 步骤4: 删除 {len(unused_muscles)} 个未被使用的Muscle节点")
        for muscle_name in unused_muscles:
            result = session.run("""
                MATCH (m:Muscle {name_zh: $name})
                DETACH DELETE m
                RETURN count(*) as deleted
            """, name=muscle_name)
            print(f"   🗑️ 删除: {muscle_name}")
    
    # 5. 验证结果
    print("\n📊 步骤5: 验证结果")
    result = session.run("MATCH (m:Muscle) RETURN count(m) as cnt")
    final_count = result.single()["cnt"]
    print(f"   清理后Muscle节点数: {final_count}")
    
    # 检查TARGETS_PRIMARY关系
    result = session.run("""
        MATCH (e:Exercise)-[:TARGETS_PRIMARY]->(m:Muscle)
        RETURN count(DISTINCT e) as exercises, count(DISTINCT m) as muscles
    """)
    stats = result.single()
    print(f"   有TARGETS_PRIMARY关系的Exercise: {stats['exercises']}")
    print(f"   有TARGETS_PRIMARY关系的Muscle: {stats['muscles']}")

print("\n" + "=" * 70)
print("✅ 清理完成!")
print("=" * 70)

driver.close()
