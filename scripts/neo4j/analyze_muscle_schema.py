"""分析Muscle节点的字段一致性"""
from neo4j import GraphDatabase
from collections import defaultdict

driver = GraphDatabase.driver("bolt://neo4j:7687", auth=("neo4j", "build_body_2024"))
session = driver.session()

# 获取所有Muscle节点及其属性
result = session.run("""
    MATCH (m:Muscle)
    RETURN m, keys(m) as props
    ORDER BY m.name_zh
""")

muscles = []
all_props = set()
prop_counts = defaultdict(int)

for record in result:
    node = record["m"]
    props = record["props"]
    all_props.update(props)
    for p in props:
        prop_counts[p] += 1
    muscles.append({
        "name_zh": node.get("name_zh", "N/A"),
        "props": set(props),
        "prop_count": len(props)
    })

print(f"=" * 60)
print(f"Muscle节点总数: {len(muscles)}")
print(f"=" * 60)

print(f"\n📊 所有属性及出现次数:")
for prop, count in sorted(prop_counts.items(), key=lambda x: -x[1]):
    pct = count / len(muscles) * 100
    status = "✅" if pct == 100 else "⚠️" if pct > 50 else "❌"
    print(f"  {status} {prop}: {count}/{len(muscles)} ({pct:.1f}%)")

# 按属性数量分组
print(f"\n📊 按属性数量分组:")
by_prop_count = defaultdict(list)
for m in muscles:
    by_prop_count[m["prop_count"]].append(m["name_zh"])

for count, names in sorted(by_prop_count.items()):
    print(f"  {count}个属性: {len(names)}个节点")
    if len(names) <= 5:
        for n in names:
            print(f"    - {n}")

# 找出属性不完整的节点
print(f"\n📊 属性不完整的节点（少于最大属性数）:")
max_props = max(m["prop_count"] for m in muscles)
incomplete = [m for m in muscles if m["prop_count"] < max_props]
print(f"  最大属性数: {max_props}")
print(f"  不完整节点数: {len(incomplete)}")

if incomplete:
    # 显示缺失的属性
    full_props = set()
    for m in muscles:
        if m["prop_count"] == max_props:
            full_props = m["props"]
            break
    
    print(f"\n  完整属性列表: {sorted(full_props)}")
    print(f"\n  不完整节点详情:")
    for m in incomplete[:10]:
        missing = full_props - m["props"]
        print(f"    - {m['name_zh']}: 缺少 {sorted(missing)}")

driver.close()
