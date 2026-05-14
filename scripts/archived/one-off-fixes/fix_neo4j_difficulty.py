#!/usr/bin/env python3
"""
修复Neo4j Exercise节点的difficulty字段

问题：当前所有Exercise.difficulty都是"中级"
解决：从源文件读取正确的difficulty_zh并更新Neo4j

源文件位置：yuzhen-backend/storage/app/public/exercises_v2/
"""
import os
import json
import glob
from pathlib import Path
from neo4j import GraphDatabase

# Neo4j连接配置
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'build_body_2024')

# 源文件目录
SOURCE_DIR = "/app/../yuzhen-backend/storage/app/public/exercises_v2"

def load_exercises_from_source():
    """从源文件加载所有动作的difficulty信息"""
    exercises = {}
    
    # 遍历所有data.json文件
    pattern = os.path.join(SOURCE_DIR, "**/data.json")
    files = glob.glob(pattern, recursive=True)
    
    print(f"找到 {len(files)} 个源文件")
    
    for filepath in files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            exercise_id = data.get('id')
            difficulty_zh = data.get('difficulty_zh', '中级')
            difficulty_en = data.get('difficulty_en', 'Intermediate')
            
            if exercise_id:
                exercises[exercise_id] = {
                    'difficulty_zh': difficulty_zh,
                    'difficulty_en': difficulty_en
                }
        except Exception as e:
            print(f"读取文件失败 {filepath}: {e}")
    
    print(f"成功加载 {len(exercises)} 个动作的difficulty信息")
    return exercises

def analyze_difficulty_distribution(exercises):
    """分析difficulty分布"""
    distribution = {}
    for ex_id, data in exercises.items():
        diff = data['difficulty_zh']
        distribution[diff] = distribution.get(diff, 0) + 1
    
    print("\n=== 源文件difficulty分布 ===")
    for diff, count in sorted(distribution.items(), key=lambda x: -x[1]):
        print(f"  {diff}: {count}")
    
    return distribution

def update_neo4j_difficulty(exercises, dry_run=True):
    """更新Neo4j中的difficulty字段"""
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    updated_count = 0
    error_count = 0
    
    with driver.session() as session:
        # 先检查当前Neo4j中的difficulty分布
        result = session.run("""
            MATCH (e:Exercise)
            RETURN e.difficulty as difficulty, count(*) as cnt
            ORDER BY cnt DESC
        """)
        
        print("\n=== Neo4j当前difficulty分布 ===")
        for record in result:
            print(f"  {record['difficulty']}: {record['cnt']}")
        
        if dry_run:
            print("\n[DRY RUN] 以下是将要执行的更新：")
        else:
            print("\n开始更新Neo4j...")
        
        # 批量更新
        batch_size = 100
        exercise_list = list(exercises.items())
        
        for i in range(0, len(exercise_list), batch_size):
            batch = exercise_list[i:i+batch_size]
            
            for ex_id, data in batch:
                try:
                    if dry_run:
                        # 只检查是否存在
                        result = session.run("""
                            MATCH (e:Exercise {id: $id})
                            RETURN e.id as id, e.difficulty as current_difficulty
                        """, id=ex_id)
                        record = result.single()
                        if record:
                            current = record['current_difficulty']
                            new = data['difficulty_zh']
                            if current != new:
                                print(f"  ID {ex_id}: '{current}' -> '{new}'")
                                updated_count += 1
                    else:
                        # 实际更新
                        result = session.run("""
                            MATCH (e:Exercise {id: $id})
                            SET e.difficulty = $difficulty_zh,
                                e.difficulty_en = $difficulty_en
                            RETURN e.id as id
                        """, id=ex_id, 
                            difficulty_zh=data['difficulty_zh'],
                            difficulty_en=data['difficulty_en'])
                        
                        if result.single():
                            updated_count += 1
                            
                except Exception as e:
                    error_count += 1
                    if error_count <= 5:
                        print(f"  更新失败 ID {ex_id}: {e}")
            
            if not dry_run and i % 500 == 0:
                print(f"  已处理 {i + len(batch)}/{len(exercise_list)}")
        
        # 验证更新结果
        if not dry_run:
            result = session.run("""
                MATCH (e:Exercise)
                RETURN e.difficulty as difficulty, count(*) as cnt
                ORDER BY cnt DESC
            """)
            
            print("\n=== 更新后Neo4j difficulty分布 ===")
            for record in result:
                print(f"  {record['difficulty']}: {record['cnt']}")
    
    driver.close()
    
    print(f"\n{'[DRY RUN] 将要更新' if dry_run else '成功更新'}: {updated_count} 个动作")
    if error_count > 0:
        print(f"错误数量: {error_count}")
    
    return updated_count

def main():
    import argparse
    parser = argparse.ArgumentParser(description='修复Neo4j Exercise节点的difficulty字段')
    parser.add_argument('--execute', action='store_true', help='实际执行更新（默认为dry run）')
    args = parser.parse_args()
    
    print("=" * 60)
    print("修复Neo4j Exercise节点的difficulty字段")
    print("=" * 60)
    
    # 1. 加载源文件
    exercises = load_exercises_from_source()
    
    if not exercises:
        print("未找到任何动作数据，退出")
        return
    
    # 2. 分析分布
    analyze_difficulty_distribution(exercises)
    
    # 3. 更新Neo4j
    dry_run = not args.execute
    update_neo4j_difficulty(exercises, dry_run=dry_run)
    
    if dry_run:
        print("\n提示：使用 --execute 参数来实际执行更新")

if __name__ == "__main__":
    main()
