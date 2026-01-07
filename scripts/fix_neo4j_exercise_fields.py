#!/usr/bin/env python3
"""
修复Neo4j Exercise节点的字段名称和difficulty值

问题：
1. 字段名称不一致：
   - difficulty -> difficulty_zh
   - difficulty_level -> difficulty_en
   - kinetic_chain -> kinetic_chain_type
   - mechanic -> mechanic_zh (需要保留mechanic_en)
   - force -> force_zh (需要保留force_en)

2. difficulty值全部是"中级"，需要从目标数据集更新正确值
"""
import json
from neo4j import GraphDatabase
from collections import Counter

# Neo4j配置
NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

# 目标数据集路径（容器内需要挂载或复制）
TARGET_FILE = "/app/data/enhanced_perfect_exercises_dataset.json"

def get_driver():
    return GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

def analyze_current_fields(driver):
    """分析当前Neo4j字段情况"""
    print("\n=== 分析当前Neo4j Exercise字段 ===")
    
    with driver.session() as session:
        # 获取一个样本节点的所有字段
        result = session.run("MATCH (e:Exercise) RETURN e LIMIT 1")
        record = result.single()
        if record:
            node = record['e']
            print("当前字段列表:")
            for k in sorted(node.keys()):
                print(f"  - {k}")
        
        # 统计difficulty分布
        result = session.run("MATCH (e:Exercise) RETURN e.difficulty as diff, count(*) as cnt ORDER BY cnt DESC")
        print("\n当前difficulty分布:")
        for record in result:
            print(f"  {record['diff'] or '(空)'}: {record['cnt']}")
        
        # 统计difficulty_level分布
        result = session.run("MATCH (e:Exercise) RETURN e.difficulty_level as diff, count(*) as cnt ORDER BY cnt DESC")
        print("\n当前difficulty_level分布:")
        for record in result:
            print(f"  {record['diff'] or '(空)'}: {record['cnt']}")

def rename_fields(driver):
    """重命名字段"""
    print("\n=== 重命名字段 ===")
    
    field_renames = [
        ("difficulty", "difficulty_zh"),
        ("difficulty_level", "difficulty_en"),
        ("kinetic_chain", "kinetic_chain_type"),
    ]
    
    with driver.session() as session:
        for old_name, new_name in field_renames:
            # 检查旧字段是否存在
            result = session.run(f"MATCH (e:Exercise) WHERE e.{old_name} IS NOT NULL RETURN count(e) as cnt")
            count = result.single()['cnt']
            
            if count > 0:
                print(f"重命名 {old_name} -> {new_name} ({count}个节点)")
                session.run(f"""
                    MATCH (e:Exercise) 
                    WHERE e.{old_name} IS NOT NULL
                    SET e.{new_name} = e.{old_name}
                    REMOVE e.{old_name}
                """)
            else:
                print(f"跳过 {old_name} -> {new_name} (无数据)")

def load_difficulty_from_dataset():
    """从目标数据集加载difficulty数据"""
    print(f"\n=== 从数据集加载difficulty ===")
    
    try:
        with open(TARGET_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        exercises = data.get('enhanced_perfect_exercises', [])
        print(f"数据集动作数量: {len(exercises)}")
        
        difficulty_map = {}
        for ex in exercises:
            ex_id = ex.get('id')
            if ex_id:
                difficulty_map[ex_id] = {
                    'zh': ex.get('difficulty_zh', ''),
                    'en': ex.get('difficulty_en', '')
                }
        
        return difficulty_map
    except FileNotFoundError:
        print(f"警告: 数据集文件不存在: {TARGET_FILE}")
        print("请先将数据集复制到容器内")
        return None

def update_difficulty_from_dataset(driver, difficulty_map):
    """从数据集更新difficulty值"""
    if not difficulty_map:
        print("跳过difficulty更新（无数据）")
        return
    
    print(f"\n=== 更新difficulty值 ===")
    
    updated = 0
    with driver.session() as session:
        for ex_id, diff_data in difficulty_map.items():
            diff_zh = diff_data['zh']
            diff_en = diff_data['en']
            
            if diff_zh or diff_en:
                result = session.run("""
                    MATCH (e:Exercise {id: $id})
                    SET e.difficulty_zh = $diff_zh,
                        e.difficulty_en = $diff_en
                    RETURN e.id
                """, id=ex_id, diff_zh=diff_zh, diff_en=diff_en)
                
                if result.single():
                    updated += 1
    
    print(f"更新了 {updated} 个节点的difficulty")

def verify_results(driver):
    """验证修复结果"""
    print("\n=== 验证修复结果 ===")
    
    with driver.session() as session:
        # 统计difficulty_zh分布
        result = session.run("MATCH (e:Exercise) RETURN e.difficulty_zh as diff, count(*) as cnt ORDER BY cnt DESC")
        print("\n修复后difficulty_zh分布:")
        for record in result:
            print(f"  {record['diff'] or '(空)'}: {record['cnt']}")
        
        # 检查旧字段是否还存在
        result = session.run("MATCH (e:Exercise) WHERE e.difficulty IS NOT NULL RETURN count(e) as cnt")
        old_count = result.single()['cnt']
        if old_count > 0:
            print(f"\n警告: 仍有 {old_count} 个节点有旧的difficulty字段")
        else:
            print("\n✅ 旧的difficulty字段已全部移除")

def main():
    print("=" * 60)
    print("修复Neo4j Exercise节点字段")
    print("=" * 60)
    
    driver = get_driver()
    
    try:
        # 1. 分析当前状态
        analyze_current_fields(driver)
        
        # 2. 重命名字段
        rename_fields(driver)
        
        # 3. 加载数据集
        difficulty_map = load_difficulty_from_dataset()
        
        # 4. 更新difficulty值
        update_difficulty_from_dataset(driver, difficulty_map)
        
        # 5. 验证结果
        verify_results(driver)
        
        print("\n✅ 修复完成!")
        
    finally:
        driver.close()

if __name__ == "__main__":
    main()
