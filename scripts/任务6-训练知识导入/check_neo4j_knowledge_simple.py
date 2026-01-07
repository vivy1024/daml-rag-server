"""
简单检查Neo4j中的知识节点
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from neo4j import GraphDatabase


def check_neo4j():
    """检查Neo4j知识覆盖"""
    print("\n" + "="*60)
    print("检查Neo4j知识覆盖")
    print("="*60)
    
    # 连接Neo4j
    uri = "bolt://fitness_neo4j:7687"
    driver = GraphDatabase.driver(uri, auth=("neo4j", "build_body_2024"))
    
    with driver.session() as session:
        # 1. 节点类型统计
        print("\n1. 节点类型统计:")
        result = session.run("""
            MATCH (n)
            RETURN labels(n)[0] as label, count(n) as count
            ORDER BY count DESC
        """)
        
        total = 0
        for record in result:
            label = record["label"]
            count = record["count"]
            total += count
            print(f"   {label}: {count}")
        
        print(f"\n   总节点数: {total}")
        
        # 2. 检查训练知识节点
        print("\n2. 训练知识节点检查:")
        
        knowledge_labels = [
            'TrainingKnowledge',
            'PeriodizationModel',
            'WorkoutProgram',
            'TrainingVolume',
            'StrengthStandard',
            'ACSMStandard',
            'NSCAStandard'
        ]
        
        for label in knowledge_labels:
            result = session.run(f"MATCH (n:{label}) RETURN count(n) as count")
            record = result.single()
            count = record["count"] if record else 0
            status = "✅" if count > 0 else "❌"
            print(f"   {status} {label}: {count}")
        
        # 3. 检查Muscle节点的训练属性
        print("\n3. Muscle节点训练属性检查:")
        result = session.run("""
            MATCH (m:Muscle)
            RETURN m.name_zh as name,
                   m.training_frequency as freq,
                   m.recovery_time as recovery,
                   m.mev as mev,
                   m.mav as mav,
                   m.mrv as mrv
            LIMIT 5
        """)
        
        records = list(result)
        if records:
            print(f"   ✅ 找到 {len(records)} 个Muscle节点（显示前5个）:")
            for record in records:
                name = record["name"] or "Unknown"
                freq = record["freq"] or "N/A"
                recovery = record["recovery"] or "N/A"
                mev = record["mev"] or "N/A"
                mav = record["mav"] or "N/A"
                mrv = record["mrv"] or "N/A"
                print(f"      {name}: 频率={freq}, 恢复={recovery}, MEV={mev}, MAV={mav}, MRV={mrv}")
        else:
            print("   ❌ 未找到Muscle节点或缺少训练属性")
        
        # 4. 检查Exercise节点数量
        print("\n4. Exercise节点统计:")
        result = session.run("MATCH (e:Exercise) RETURN count(e) as count")
        record = result.single()
        count = record["count"] if record else 0
        print(f"   Exercise节点: {count}")
        
        # 5. 检查Food节点数量
        print("\n5. Food节点统计:")
        result = session.run("MATCH (f:Food) RETURN count(f) as count")
        record = result.single()
        count = record["count"] if record else 0
        print(f"   Food节点: {count}")
    
    driver.close()


def generate_recommendations():
    """生成改进建议"""
    print("\n" + "="*60)
    print("改进建议")
    print("="*60)
    
    print("\n需要添加到Neo4j的训练知识:")
    print("\n1. [P1] 周期化模型 (PeriodizationModel)")
    print("   - 文件: periodization-models.json")
    print("   - 内容: 线性周期化、波浪式周期化、块状周期化等")
    print("   - 节点数: ~5个模型")
    
    print("\n2. [P1] 训练计划模板 (WorkoutProgram)")
    print("   - 文件: workout-programs.json")
    print("   - 内容: 预设的训练计划模板")
    print("   - 节点数: ~10-20个计划")
    
    print("\n3. [P1] 训练量标准 (TrainingVolume)")
    print("   - 文件: training-volume-landmarks.json")
    print("   - 内容: MEV/MAV/MRV标准")
    print("   - 节点数: ~50个肌群标准")
    
    print("\n4. [P1] 力量标准 (StrengthStandard)")
    print("   - 文件: strength-standards.json")
    print("   - 内容: 不同水平的力量标准")
    print("   - 节点数: ~100个标准")
    
    print("\n5. [P2] ACSM标准 (ACSMStandard)")
    print("   - 文件: acsm_standards/*.json")
    print("   - 内容: FITT原则、心率指南等")
    print("   - 节点数: ~10-20个标准")
    
    print("\n6. [P2] NSCA标准 (NSCAStandard)")
    print("   - 文件: nsca_standards/*.json")
    print("   - 内容: 周期化、力量训练要点")
    print("   - 节点数: ~10-20个标准")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("Neo4j知识覆盖检查")
    print("="*60)
    
    try:
        check_neo4j()
        generate_recommendations()
        
        print("\n" + "="*60)
        print("✅ 检查完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
