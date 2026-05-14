#!/usr/bin/env python3
"""
数据清理脚本

执行用户方案：
1. 从 description_zh 提取步骤，补充到 correct_steps_zh
2. 删除 description_zh 和 description_en（等待重新爬取）
3. 保留 description_zh_professional 作为临时描述
"""

import json
import sys
import os
import re
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("Exercise 数据清理")
print("=" * 80)

# 读取数据
db_file = 'data/enhanced_perfect_exercises_dataset.json'
print(f"\n读取数据库文件: {db_file}")

with open(db_file, 'r', encoding='utf-8') as f:
    db_data = json.load(f)

if isinstance(db_data, dict):
    if 'enhanced_perfect_exercises' in db_data:
        exercises = db_data['enhanced_perfect_exercises']
    elif 'exercises' in db_data:
        exercises = db_data['exercises']
else:
    exercises = db_data

print(f"总动作数: {len(exercises)}")

# 统计
stats = {
    "total": len(exercises),
    "extracted_from_desc_zh": 0,
    "already_has_steps_zh": 0,
    "need_translation": 0,
    "deleted_desc_zh": 0,
    "deleted_desc_en": 0,
}

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

print(f"\n连接 Neo4j: {NEO4J_URI}")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("✅ Neo4j 连接成功")
except Exception as e:
    print(f"❌ Neo4j 连接失败: {e}")
    sys.exit(1)

def extract_steps_from_description(desc_zh):
    """从 description_zh 中提取步骤"""
    if not desc_zh:
        return []
    
    steps = []
    
    # 方法1: 匹配 "正确步骤： 1。...2。...3。..."
    if '正确步骤' in desc_zh or '步骤：' in desc_zh:
        # 提取步骤部分
        parts = re.split(r'正确步骤[：:]\s*', desc_zh)
        if len(parts) > 1:
            steps_text = parts[1]
        else:
            parts = re.split(r'步骤[：:]\s*', desc_zh)
            if len(parts) > 1:
                steps_text = parts[1]
            else:
                steps_text = desc_zh
        
        # 分割步骤（按 "1。" "2。" "3。" 或 "1. " "2. " "3. "）
        step_matches = re.findall(r'[1-9]\d*[。\.](.+?)(?=[1-9]\d*[。\.]|$)', steps_text, re.DOTALL)
        if step_matches:
            steps = [s.strip() for s in step_matches if s.strip()]
    
    # 方法2: 如果没有找到，尝试匹配 "- xxx\n- xxx"
    if not steps and desc_zh.count('- ') >= 2:
        step_matches = re.findall(r'-\s*(.+?)(?=\n-|\n\n|$)', desc_zh, re.DOTALL)
        if step_matches:
            steps = [s.strip() for s in step_matches if s.strip() and len(s.strip()) > 10]
    
    return steps

def update_exercise_in_neo4j(session, exercise_id, correct_steps_zh, delete_descriptions=True):
    """更新 Neo4j 中的 Exercise 节点"""
    
    # 构建更新语句
    if delete_descriptions:
        # 删除 description_zh 和 description_en
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        SET e.correct_steps_zh = $correct_steps_zh,
            e.description_zh = null,
            e.description_en = null
        RETURN e.id as id, e.name_zh as name_zh
        """
    else:
        # 仅更新 correct_steps_zh
        query = """
        MATCH (e:Exercise {id: $exercise_id})
        SET e.correct_steps_zh = $correct_steps_zh
        RETURN e.id as id, e.name_zh as name_zh
        """
    
    result = session.run(query, exercise_id=exercise_id, correct_steps_zh=correct_steps_zh)
    return result.single()

# 处理每个动作
print("\n开始处理...")
print("-" * 80)

processed = 0
errors = []

with driver.session() as session:
    for exercise in exercises:
        ex_id = exercise.get('id')
        name_zh = exercise.get('name_zh', '')
        desc_zh = (exercise.get('description_zh') or '').strip()
        desc_en = (exercise.get('description_en') or '').strip()
        steps_zh = exercise.get('correct_steps_zh') or []
        steps_en = exercise.get('correct_steps_en') or []
        
        try:
            # 检查是否已有 correct_steps_zh
            if steps_zh and len(steps_zh) > 0:
                stats["already_has_steps_zh"] += 1
                
                # 仅删除 description_zh 和 description_en
                if desc_zh or desc_en:
                    result = update_exercise_in_neo4j(session, ex_id, steps_zh, delete_descriptions=True)
                    if result:
                        stats["deleted_desc_zh"] += 1 if desc_zh else 0
                        stats["deleted_desc_en"] += 1 if desc_en else 0
                
                processed += 1
                if processed % 100 == 0:
                    print(f"  已处理: {processed}/{len(exercises)}")
                continue
            
            # 尝试从 description_zh 提取步骤
            if desc_zh:
                extracted_steps = extract_steps_from_description(desc_zh)
                
                if extracted_steps and len(extracted_steps) >= 2:
                    # 成功提取步骤
                    result = update_exercise_in_neo4j(session, ex_id, extracted_steps, delete_descriptions=True)
                    if result:
                        stats["extracted_from_desc_zh"] += 1
                        stats["deleted_desc_zh"] += 1
                        stats["deleted_desc_en"] += 1 if desc_en else 0
                        
                        if stats["extracted_from_desc_zh"] <= 5:
                            print(f"\n✅ ID={ex_id}, {name_zh}")
                            print(f"   提取了 {len(extracted_steps)} 个步骤")
                            print(f"   第一步: {extracted_steps[0][:50]}...")
                    
                    processed += 1
                    if processed % 100 == 0:
                        print(f"  已处理: {processed}/{len(exercises)}")
                    continue
            
            # 无法从 description_zh 提取，需要翻译
            stats["need_translation"] += 1
            
            # 暂时不翻译，仅删除 description
            if desc_zh or desc_en:
                result = update_exercise_in_neo4j(session, ex_id, [], delete_descriptions=True)
                if result:
                    stats["deleted_desc_zh"] += 1 if desc_zh else 0
                    stats["deleted_desc_en"] += 1 if desc_en else 0
            
            processed += 1
            if processed % 100 == 0:
                print(f"  已处理: {processed}/{len(exercises)}")
        
        except Exception as e:
            errors.append({
                "id": ex_id,
                "name_zh": name_zh,
                "error": str(e)
            })
            print(f"\n❌ 错误: ID={ex_id}, {name_zh}: {e}")

driver.close()

# 输出结果
print("\n\n" + "=" * 80)
print("处理完成")
print("=" * 80)

print(f"\n总动作数: {stats['total']}")
print(f"已有 correct_steps_zh: {stats['already_has_steps_zh']}")
print(f"从 description_zh 提取: {stats['extracted_from_desc_zh']}")
print(f"需要翻译: {stats['need_translation']}")
print(f"删除 description_zh: {stats['deleted_desc_zh']}")
print(f"删除 description_en: {stats['deleted_desc_en']}")

if errors:
    print(f"\n错误数量: {len(errors)}")
    print("\n前5个错误:")
    for error in errors[:5]:
        print(f"  ID={error['id']}, {error['name_zh']}: {error['error']}")

print("\n✅ 数据清理完成！")
print("\n后续步骤：")
print("  1. 对于需要翻译的 28 个动作，可以使用 Ollama 翻译")
print("  2. 等待重新爬取 description_zh 和 description_en")
print("  3. description_zh_professional 已保留作为临时描述")

print("\n" + "=" * 80)
