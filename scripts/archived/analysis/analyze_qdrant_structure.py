#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
分析Qdrant数据结构
诊断向量检索精准度问题
"""

from qdrant_client import QdrantClient
import json

client = QdrantClient(host='qdrant', port=6333)

# 1. 获取集合信息
info = client.get_collection('fitness_exercises_v2')
print("=" * 80)
print("📊 Qdrant集合信息")
print("=" * 80)
print(f"集合名称: fitness_exercises_v2")
print(f"向量数量: {info.points_count}")
print(f"向量维度: {info.config.params.vectors.size}")
print(f"距离度量: {info.config.params.vectors.distance}")

# 2. 获取样本数据
print("\n" + "=" * 80)
print("📋 样本数据分析（前5个）")
print("=" * 80)

points, _ = client.scroll(
    'fitness_exercises_v2',
    limit=5,
    with_payload=True,
    with_vectors=False
)

for i, point in enumerate(points, 1):
    print(f"\n{i}. ID={point.id}")
    print(f"   Payload字段: {list(point.payload.keys())}")
    print(f"   内容:")
    for key, value in point.payload.items():
        if key != 'search_text':  # search_text太长，单独显示
            print(f"     - {key}: {value}")
    if 'search_text' in point.payload:
        search_text = point.payload['search_text']
        print(f"     - search_text: {search_text[:100]}..." if len(search_text) > 100 else f"     - search_text: {search_text}")

# 3. 统计payload字段
print("\n" + "=" * 80)
print("📊 Payload字段统计")
print("=" * 80)

# 获取更多样本进行统计
points, _ = client.scroll(
    'fitness_exercises_v2',
    limit=100,
    with_payload=True,
    with_vectors=False
)

field_stats = {}
for point in points:
    for key in point.payload.keys():
        if key not in field_stats:
            field_stats[key] = {
                'count': 0,
                'sample_values': set()
            }
        field_stats[key]['count'] += 1
        
        # 收集样本值（限制数量）
        value = point.payload[key]
        if isinstance(value, (str, int, float)) and len(field_stats[key]['sample_values']) < 5:
            field_stats[key]['sample_values'].add(str(value))

print(f"\n共分析 {len(points)} 个样本")
print(f"发现 {len(field_stats)} 个字段:\n")

for field, stats in sorted(field_stats.items()):
    print(f"  {field}:")
    print(f"    - 出现次数: {stats['count']}/{len(points)}")
    if stats['sample_values']:
        print(f"    - 样本值: {', '.join(list(stats['sample_values'])[:5])}")

# 4. 分析"山"这个动作
print("\n" + "=" * 80)
print("🏔️ 分析'山'这个动作")
print("=" * 80)

# 搜索包含"山"的动作
points, _ = client.scroll(
    'fitness_exercises_v2',
    scroll_filter={
        "must": [
            {
                "key": "name_zh",
                "match": {"value": "山"}
            }
        ]
    },
    limit=10,
    with_payload=True,
    with_vectors=False
)

if points:
    for point in points:
        print(f"\nID={point.id}")
        print(f"名称: {point.payload.get('name_zh')} / {point.payload.get('name_en')}")
        print(f"主要肌群: {point.payload.get('primary_muscle_zh')}")
        print(f"器械: {point.payload.get('equipment_zh')}")
        print(f"难度: {point.payload.get('difficulty')}")
        print(f"搜索文本: {point.payload.get('search_text')}")
else:
    print("未找到'山'这个动作")

# 5. 建议的优化方案
print("\n" + "=" * 80)
print("💡 优化建议")
print("=" * 80)

print("""
基于当前数据结构，建议以下优化：

1. 添加category字段（动作分类）
   - 力量训练 (strength_training)
   - 瑜伽 (yoga)
   - 拉伸 (stretching)
   - 有氧运动 (cardio)
   
2. 优化search_text构建
   当前: "名称 名称 肌群 器械 难度"
   建议: "名称 [分类] 肌群 器械 难度 [训练类型]"
   
3. 添加训练类型标签
   - 复合动作 vs 孤立动作
   - 推 vs 拉 vs 腿
   
4. 在Layer 1添加category过滤
   查询"胸部训练"时，自动添加category=strength_training过滤
   
5. 提升search_text权重
   将category和训练类型放在search_text开头，提高权重
""")

print("\n" + "=" * 80)
print("✅ 分析完成")
print("=" * 80)
