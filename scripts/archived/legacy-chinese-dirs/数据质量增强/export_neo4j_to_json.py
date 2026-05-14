#!/usr/bin/env python3
"""从Neo4j导出Exercise数据到JSON文件"""

from neo4j import GraphDatabase
import json
from datetime import datetime

# Neo4j连接配置
NEO4J_URI = "bolt://fitness_neo4j:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"

def export_exercises_from_neo4j():
    """从Neo4j导出所有Exercise数据"""
    
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    
    print("正在从Neo4j读取Exercise数据...")
    
    with driver.session() as session:
        # 获取所有Exercise节点的所有字段
        result = session.run("""
            MATCH (e:Exercise)
            RETURN e
            ORDER BY e.id
        """)
        
        exercises = []
        for record in result:
            node = record["e"]
            # 将Neo4j节点转换为字典，处理特殊类型
            exercise_dict = {}
            for key, value in dict(node).items():
                # 转换DateTime对象为ISO格式字符串
                if hasattr(value, 'iso_format'):
                    exercise_dict[key] = value.iso_format()
                elif hasattr(value, 'isoformat'):
                    exercise_dict[key] = value.isoformat()
                else:
                    exercise_dict[key] = value
            exercises.append(exercise_dict)
        
        print(f"✅ 成功读取 {len(exercises)} 个Exercise节点")
    
    driver.close()
    
    # 读取现有的JSON文件
    print("\n正在读取现有数据文件...")
    try:
        with open('data/enhanced_perfect_exercises_dataset.json', 'r', encoding='utf-8') as f:
            file_data = json.load(f)
    except Exception as e:
        print(f"⚠️  读取现有文件失败: {e}")
        file_data = {}
    
    # 更新数据
    file_data['enhanced_perfect_exercises'] = exercises
    file_data['export_info'] = {
        'export_time': datetime.now().isoformat(),
        'total_exercises': len(exercises),
        'source': 'Neo4j Database',
        'version': '1.0.0'
    }
    
    # 写入文件
    print("\n正在写入数据文件...")
    with open('data/enhanced_perfect_exercises_dataset.json', 'w', encoding='utf-8') as f:
        json.dump(file_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 成功导出 {len(exercises)} 个Exercise到数据文件")
    
    # 验证
    print("\n验证导出结果...")
    rom_count = len([e for e in exercises if 'rom_requirements' in e and e['rom_requirements']])
    print(f"✅ 有ROM数据的Exercise: {rom_count} 个")
    print(f"✅ ROM覆盖率: {rom_count/len(exercises)*100:.1f}%")
    
    print("\n" + "=" * 70)
    print("✅ Neo4j数据已成功导出到数据文件！")
    print("=" * 70)

if __name__ == "__main__":
    export_exercises_from_neo4j()
