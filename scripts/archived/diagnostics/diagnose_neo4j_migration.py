#!/usr/bin/env python3
"""诊断Neo4j迁移问题 - 详细分析哪些数据被跳过"""
from neo4j import GraphDatabase
import sys

LOCAL_URI = "bolt://fitness_neo4j:7687"
LOCAL_USER = "neo4j"
LOCAL_PASSWORD = "build_body_2024"

PRODUCTION_URI = "bolt://182.92.78.183:32372"
PRODUCTION_USER = "neo4j"
PRODUCTION_PASSWORD = "build_body_2024"

NODE_UNIQUE_KEYS = {
    'Exercise': 'exercise_id',
    'Muscle': 'muscle_id',
    'Equipment': 'equipment_id',
    'Food': 'food_code',
    'Nutrient': 'name',
    'NutrientCategory': 'name',
    'TrainingGoal': 'name',
    'TrainingLevel': 'name',
    'TrainingParams': 'name',
    'MechanicType': 'name',
    'ForceType': 'name',
    'GripType': 'name',
    'KineticChain': 'name',
    'InjuryType': 'name',
    'PosturalIssue': 'name',
    'Joint': 'name',
    'StrengthStandard': 'name',
    'WorkoutProgram': 'name',
    'TrainingPhase': 'name',
    'PeriodizationModel': 'name',
    'RehabilitationPhase': 'name',
    'ACSMStandard': 'name',
    'NSCAStandard': 'name',
}

def get_all_labels(driver):
    """获取所有节点标签"""
    with driver.session() as session:
        result = session.run("CALL db.labels()")
        return [record[0] for record in result]

def check_nodes_by_label(driver, label, env_name):
    """检查指定标签的节点"""
    unique_key = NODE_UNIQUE_KEYS.get(label, 'name')
    
    with driver.session() as session:
        # 总数
        total = session.run(f"MATCH (n:{label}) RETURN count(n) as count").single()["count"]
        
        # 有唯一键的数量
        valid = session.run(f"""
            MATCH (n:{label})
            WHERE n.{unique_key} IS NOT NULL
            RETURN count(n) as count
        """).single()["count"]
        
        # 缺少唯一键的数量
        invalid = total - valid
        
        # 示例：缺少唯一键的节点
        invalid_samples = []
        if invalid > 0:
            result = session.run(f"""
                MATCH (n:{label})
                WHERE n.{unique_key} IS NULL
                RETURN properties(n) as props
                LIMIT 3
            """)
            invalid_samples = [record['props'] for record in result]
    
    return {
        'total': total,
        'valid': valid,
        'invalid': invalid,
        'invalid_samples': invalid_samples
    }

def main():
    print("=" * 60)
    print("Neo4j迁移诊断")
    print("=" * 60)
    
    local_driver = GraphDatabase.driver(LOCAL_URI, auth=(LOCAL_USER, LOCAL_PASSWORD))
    production_driver = GraphDatabase.driver(PRODUCTION_URI, auth=(PRODUCTION_USER, PRODUCTION_PASSWORD))
    
    try:
        print("\n📋 本地数据库分析:")
        labels = get_all_labels(local_driver)
        
        total_valid = 0
        total_invalid = 0
        problem_labels = []
        
        for label in labels:
            unique_key = NODE_UNIQUE_KEYS.get(label, 'name')
            stats = check_nodes_by_label(local_driver, label, "本地")
            
            if stats['invalid'] > 0:
                problem_labels.append(label)
                print(f"\n⚠️  {label} (唯一键: {unique_key})")
                print(f"  总数: {stats['total']}")
                print(f"  有效: {stats['valid']}")
                print(f"  无效: {stats['invalid']}")
                if stats['invalid_samples']:
                    print(f"  示例:")
                    for sample in stats['invalid_samples']:
                        print(f"    {sample}")
            else:
                print(f"✅ {label}: {stats['total']} 个（全部有效）")
            
            total_valid += stats['valid']
            total_invalid += stats['invalid']
        
        print(f"\n📊 汇总:")
        print(f"  总节点: {total_valid + total_invalid}")
        print(f"  有效节点: {total_valid}")
        print(f"  无效节点: {total_invalid}")
        print(f"  问题标签: {len(problem_labels)}")
        
        if problem_labels:
            print(f"\n🔧 建议:")
            print(f"  以下标签有缺少唯一键的节点:")
            for label in problem_labels:
                unique_key = NODE_UNIQUE_KEYS.get(label, 'name')
                print(f"    - {label} (需要 {unique_key})")
        
        # 检查生产环境
        print(f"\n📋 生产环境状态:")
        with production_driver.session() as session:
            prod_nodes = session.run("MATCH (n) RETURN count(n) as count").single()["count"]
            prod_rels = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]
        print(f"  节点: {prod_nodes}")
        print(f"  关系: {prod_rels}")
        
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        local_driver.close()
        production_driver.close()

if __name__ == "__main__":
    main()
