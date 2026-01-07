"""验证Muscle节点查询"""
from neo4j import GraphDatabase

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "build_body_2024"))

with driver.session() as session:
    print("=" * 60)
    print("TrainingSplitDesigner查询测试")
    print("=" * 60)
    
    # 测试几个常用肌群
    test_muscles = ["胸部", "背阔肌", "股四头肌", "臀部", "三角肌前束"]
    
    for muscle in test_muscles:
        result = session.run("""
            MATCH (m:Muscle {name_zh: $muscle})<-[:TARGETS_PRIMARY]-(e:Exercise)
            RETURN m.name_zh as muscle, count(e) as exercise_count
        """, muscle=muscle)
        record = result.single()
        if record and record["exercise_count"] > 0:
            print(f"✅ {muscle}: {record['exercise_count']}个动作")
        else:
            print(f"❌ {muscle}: 查询返回空")
    
    # 验证TARGETS_PRIMARY关系总数
    result = session.run("MATCH ()-[r:TARGETS_PRIMARY]->() RETURN count(r) as count")
    count = result.single()["count"]
    print(f"\nTARGETS_PRIMARY关系总数: {count}")
    
    # 显示每个Muscle的动作数量
    print("\n" + "=" * 60)
    print("各肌群动作数量统计")
    print("=" * 60)
    result = session.run("""
        MATCH (m:Muscle)<-[:TARGETS_PRIMARY]-(e:Exercise)
        RETURN m.name_zh as muscle, count(e) as cnt
        ORDER BY cnt DESC
    """)
    for record in result:
        print(f"  {record['muscle']}: {record['cnt']}个")

driver.close()
