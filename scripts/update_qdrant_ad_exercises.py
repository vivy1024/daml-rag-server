#!/usr/bin/env python3
"""
更新Qdrant中广告动作的向量数据

修复的广告动作：
- ID 306: 杠铃交错站姿硬拉
- ID 308: 杠铃单腿硬拉  
- ID 1224: Y字伸展

这些动作之前的name_zh是广告内容，现在已修复，需要重新生成向量
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from sentence_transformers import SentenceTransformer

# 配置
QDRANT_HOST = "fitness_qdrant"
QDRANT_PORT = 6333
COLLECTION_NAME = "fitness_exercises_v2"
EMBEDDING_MODEL = "thenlper/gte-large-zh"

# 需要更新的广告动作ID
AD_EXERCISE_IDS = [306, 308, 1224]

# 数据集路径
DATASET_PATH = Path("/app/data/enhanced_perfect_exercises_dataset.json")


def build_search_text(exercise: dict) -> str:
    """构建搜索文本（与import_exercises_to_qdrant.py保持一致）"""
    parts = []
    
    # 名称（权重3x）
    name_zh = exercise.get("name_zh", "")
    if name_zh:
        parts.extend([name_zh] * 3)
    
    name_en = exercise.get("name_en", "")
    if name_en:
        parts.append(name_en)
    
    # 主要肌群（权重2x）
    primary_muscle = exercise.get("primary_muscle_zh", "")
    if primary_muscle:
        parts.extend([primary_muscle] * 2)
    
    # 次要肌群
    secondary_muscles = exercise.get("muscles_secondary_zh", [])
    if secondary_muscles and isinstance(secondary_muscles, list):
        parts.extend([m for m in secondary_muscles if isinstance(m, str)])
    
    # 所有肌群
    all_muscles = exercise.get("all_muscles_zh", [])
    if all_muscles and isinstance(all_muscles, list):
        parts.extend([m for m in all_muscles if isinstance(m, str)])
    
    # 器械
    equipment = exercise.get("equipment_zh", "")
    if equipment:
        if isinstance(equipment, list):
            parts.extend([e for e in equipment if isinstance(e, str)])
        else:
            parts.append(str(equipment))
    
    # 难度
    difficulty = exercise.get("difficulty_zh", "")
    if difficulty:
        parts.append(str(difficulty))
    
    # 力类型
    force = exercise.get("force_zh", "")
    if force:
        parts.append(str(force))
    
    # 动作类型
    mechanic = exercise.get("mechanic_zh", "")
    if mechanic:
        parts.append(str(mechanic))
    
    # 动力链
    kinetic_chain = exercise.get("kinetic_chain_type", "")
    if kinetic_chain:
        parts.append(str(kinetic_chain))
    
    # 握法
    grips = exercise.get("grips_zh", [])
    if grips:
        if isinstance(grips, list):
            parts.extend([g for g in grips if isinstance(g, str)])
        else:
            parts.append(str(grips))
    
    # 描述（截取前300字）
    description = exercise.get("description_zh", "") or ""
    if description:
        parts.append(description[:300])
    
    # 步骤说明（截取前200字）
    steps = exercise.get("correct_steps_zh", [])
    if steps and isinstance(steps, list):
        steps_text = " ".join([s for s in steps if isinstance(s, str)])[:200]
        if steps_text:
            parts.append(steps_text)
    
    # 训练参数
    rep_range = exercise.get("rep_range", "")
    if rep_range:
        parts.append(f"次数范围{rep_range}")
    
    set_range = exercise.get("set_range", "")
    if set_range:
        parts.append(f"组数范围{set_range}")
    
    return " ".join(parts)


def build_payload(exercise: dict) -> dict:
    """构建Qdrant payload（与import_exercises_to_qdrant.py保持一致）"""
    return {
        "exercise_id": exercise.get("id"),
        "name_zh": exercise.get("name_zh", ""),
        "name_en": exercise.get("name_en", ""),
        "slug": exercise.get("slug", ""),
        "description_zh": exercise.get("description_zh", ""),
        "primary_muscle_zh": exercise.get("primary_muscle_zh", ""),
        "primary_muscle_en": exercise.get("primary_muscle_en", ""),
        "muscles_secondary_zh": exercise.get("muscles_secondary_zh", []),
        "muscles_secondary_en": exercise.get("muscles_secondary_en", []),
        "all_muscles_zh": exercise.get("all_muscles_zh", []),
        "all_muscles_en": exercise.get("all_muscles_en", []),
        "equipment_zh": exercise.get("equipment_zh", ""),
        "equipment_en": exercise.get("equipment_en", ""),
        "difficulty_zh": exercise.get("difficulty_zh", ""),
        "difficulty_en": exercise.get("difficulty_en", ""),
        "force_zh": exercise.get("force_zh", ""),
        "force_en": exercise.get("force_en", ""),
        "mechanic_zh": exercise.get("mechanic_zh", ""),
        "mechanic_en": exercise.get("mechanic_en", ""),
        "kinetic_chain_type": exercise.get("kinetic_chain_type", ""),
        "safety_level": exercise.get("safety_level", ""),
        "grips_zh": exercise.get("grips_zh", []),
        "grips_en": exercise.get("grips_en", []),
        "rep_range": exercise.get("rep_range", ""),
        "set_range": exercise.get("set_range", ""),
        "rest_period": exercise.get("rest_period", ""),
        "intensity_percentage": exercise.get("intensity_percentage", ""),
        "correct_steps_zh": exercise.get("correct_steps_zh", []),
        "correct_steps_en": exercise.get("correct_steps_en", []),
    }


def main():
    print("=" * 60)
    print("更新Qdrant广告动作向量数据")
    print("=" * 60)
    
    # 1. 加载数据集
    print("\n[1/4] 加载数据集...")
    if not DATASET_PATH.exists():
        print(f"❌ 数据集不存在: {DATASET_PATH}")
        return
    
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 数据集可能是字典格式（包含enhanced_perfect_exercises键）或列表格式
    if isinstance(data, dict):
        dataset = data.get("enhanced_perfect_exercises", [])
    else:
        dataset = data
    
    # 构建ID索引
    exercises_by_id = {ex["id"]: ex for ex in dataset}
    print(f"✅ 加载 {len(dataset)} 个动作")
    
    # 2. 获取需要更新的动作
    print("\n[2/4] 获取广告动作数据...")
    ad_exercises = []
    for ex_id in AD_EXERCISE_IDS:
        if ex_id in exercises_by_id:
            ex = exercises_by_id[ex_id]
            ad_exercises.append(ex)
            print(f"  - ID {ex_id}: {ex.get('name_zh', 'N/A')}")
        else:
            print(f"  ⚠️ ID {ex_id} 不在数据集中")
    
    if not ad_exercises:
        print("❌ 没有找到需要更新的动作")
        return
    
    # 3. 加载向量模型
    print(f"\n[3/4] 加载向量模型 {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print("✅ 模型加载完成")
    
    # 4. 连接Qdrant并更新
    print(f"\n[4/4] 连接Qdrant并更新向量...")
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
    
    # 检查集合是否存在
    collections = client.get_collections().collections
    collection_names = [c.name for c in collections]
    if COLLECTION_NAME not in collection_names:
        print(f"❌ 集合 {COLLECTION_NAME} 不存在")
        return
    
    # 更新每个动作
    updated_count = 0
    for exercise in ad_exercises:
        ex_id = exercise["id"]
        name_zh = exercise.get("name_zh", "")
        
        # 构建搜索文本
        search_text = build_search_text(exercise)
        
        # 生成向量
        vector = model.encode(search_text).tolist()
        
        # 构建payload
        payload = build_payload(exercise)
        
        # 更新Qdrant（使用upsert）
        point = PointStruct(
            id=ex_id,
            vector=vector,
            payload=payload
        )
        
        client.upsert(
            collection_name=COLLECTION_NAME,
            points=[point]
        )
        
        print(f"  ✅ ID {ex_id}: {name_zh} - 向量已更新")
        updated_count += 1
    
    print("\n" + "=" * 60)
    print(f"✅ 完成！更新了 {updated_count} 个动作的向量数据")
    print("=" * 60)
    
    # 验证更新
    print("\n验证更新结果...")
    for ex_id in AD_EXERCISE_IDS:
        results = client.retrieve(
            collection_name=COLLECTION_NAME,
            ids=[ex_id]
        )
        if results:
            point = results[0]
            print(f"  ID {ex_id}: {point.payload.get('name_zh', 'N/A')}")
        else:
            print(f"  ⚠️ ID {ex_id} 未找到")


if __name__ == "__main__":
    main()
