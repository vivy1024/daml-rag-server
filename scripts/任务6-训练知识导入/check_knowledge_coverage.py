"""
检查Neo4j和Qdrant中的知识覆盖情况

对比perfect_enhanced_dataset中的训练知识与数据库中的实际数据
"""

import sys
import os
import json
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from framework.clients.neo4j_client import Neo4jClient
from framework.clients.qdrant_client import OptimizedQdrantClient


async def check_neo4j_knowledge():
    """检查Neo4j中的知识节点"""
    print("\n" + "="*60)
    print("检查Neo4j知识覆盖")
    print("="*60)
    
    client = Neo4jClient()
    
    # 1. 检查节点类型统计
    print("\n1. 节点类型统计:")
    query = """
    MATCH (n)
    RETURN labels(n)[0] as label, count(n) as count
    ORDER BY count DESC
    """
    results = client.execute_query(query)
    
    total_nodes = 0
    for r in results:
        label = r.get('label', 'Unknown')
        count = r.get('count', 0)
        total_nodes += count
        print(f"   {label}: {count}")
    
    print(f"\n   总节点数: {total_nodes}")
    
    # 2. 检查是否有训练知识相关节点
    print("\n2. 训练知识节点检查:")
    
    knowledge_labels = [
        'TrainingKnowledge',
        'PeriodizationModel',
        'WorkoutProgram',
        'TrainingVolume',
        'StrengthStandard',
        'ACSMStandard',
        'NSCAStandard',
        'TrainingPreference'
    ]
    
    for label in knowledge_labels:
        query = f"MATCH (n:{label}) RETURN count(n) as count"
        try:
            results = client.execute_query(query)
            count = results[0].get('count', 0) if results else 0
            status = "✅" if count > 0 else "❌"
            print(f"   {status} {label}: {count}")
        except Exception as e:
            print(f"   ❌ {label}: 查询失败 - {e}")
    
    # 3. 检查Muscle节点的训练相关属性
    print("\n3. Muscle节点训练属性检查:")
    query = """
    MATCH (m:Muscle)
    RETURN m.name_zh as name,
           m.training_frequency as freq,
           m.recovery_time as recovery,
           m.mev as mev,
           m.mav as mav,
           m.mrv as mrv
    LIMIT 5
    """
    results = client.execute_query(query)
    
    if results:
        print(f"   ✅ 找到 {len(results)} 个Muscle节点（显示前5个）:")
        for r in results:
            name = r.get('name', 'Unknown')
            freq = r.get('freq', 'N/A')
            recovery = r.get('recovery', 'N/A')
            mev = r.get('mev', 'N/A')
            mav = r.get('mav', 'N/A')
            mrv = r.get('mrv', 'N/A')
            print(f"      {name}: 频率={freq}, 恢复={recovery}, MEV={mev}, MAV={mav}, MRV={mrv}")
    else:
        print("   ❌ 未找到Muscle节点或缺少训练属性")
    
    client.close()


def check_qdrant_knowledge():
    """检查Qdrant中的知识向量"""
    print("\n" + "="*60)
    print("检查Qdrant知识覆盖")
    print("="*60)
    
    try:
        client = OptimizedQdrantClient()
        
        # 获取集合信息
        collections = ['fitness_exercises', 'fitness_knowledge']
        
        for collection_name in collections:
            try:
                info = client.client.get_collection(collection_name)
                print(f"\n集合: {collection_name}")
                print(f"   向量数量: {info.points_count}")
                print(f"   向量维度: {info.config.params.vectors.size}")
                
                # 搜索训练知识相关的向量
                search_queries = [
                    "周期化训练",
                    "训练分化",
                    "训练量标准",
                    "力量标准"
                ]
                
                print(f"\n   知识检索测试:")
                for query in search_queries:
                    results = client.search(
                        collection_name=collection_name,
                        query_text=query,
                        limit=1
                    )
                    if results:
                        score = results[0].score
                        status = "✅" if score > 0.5 else "⚠️"
                        print(f"      {status} '{query}': 相似度={score:.3f}")
                    else:
                        print(f"      ❌ '{query}': 未找到结果")
            
            except Exception as e:
                print(f"\n集合 {collection_name}: ❌ 不存在或访问失败 - {e}")
    
    except Exception as e:
        print(f"\n❌ Qdrant连接失败: {e}")


def check_training_knowledge_files():
    """检查训练知识文件"""
    print("\n" + "="*60)
    print("检查训练知识文件")
    print("="*60)
    
    # 检查daml-rag-server中的文件
    knowledge_dir = "/app/data/training_knowledge"
    
    if os.path.exists(knowledge_dir):
        print(f"\n✅ 训练知识目录存在: {knowledge_dir}")
        
        files = os.listdir(knowledge_dir)
        print(f"\n文件列表 ({len(files)}个):")
        for f in sorted(files):
            file_path = os.path.join(knowledge_dir, f)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                print(f"   - {f} ({size} bytes)")
            elif os.path.isdir(file_path):
                subfiles = os.listdir(file_path)
                print(f"   - {f}/ ({len(subfiles)} 文件)")
    else:
        print(f"\n❌ 训练知识目录不存在: {knowledge_dir}")
    
    # 检查perfect_enhanced_dataset中的文件
    perfect_dir = "/app/../perfect_enhanced_dataset/data/training_knowledge"
    
    if os.path.exists(perfect_dir):
        print(f"\n✅ Perfect数据集目录存在: {perfect_dir}")
        
        files = os.listdir(perfect_dir)
        print(f"\n文件列表 ({len(files)}个):")
        for f in sorted(files):
            file_path = os.path.join(perfect_dir, f)
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path)
                print(f"   - {f} ({size} bytes)")
            elif os.path.isdir(file_path):
                subfiles = os.listdir(file_path)
                print(f"   - {f}/ ({len(subfiles)} 文件)")
    else:
        print(f"\n⚠️ Perfect数据集目录不存在: {perfect_dir}")


def generate_recommendations():
    """生成改进建议"""
    print("\n" + "="*60)
    print("改进建议")
    print("="*60)
    
    recommendations = []
    
    # 基于检查结果生成建议
    recommendations.append({
        "priority": "P1",
        "task": "添加训练知识节点到Neo4j",
        "description": "将periodization-models.json、workout-programs.json等训练知识导入Neo4j",
        "files": [
            "periodization-models.json",
            "workout-programs.json",
            "training-volume-landmarks.json",
            "strength-standards.json"
        ]
    })
    
    recommendations.append({
        "priority": "P1",
        "task": "添加ACSM/NSCA标准到Neo4j",
        "description": "导入ACSM和NSCA的训练标准和指南",
        "files": [
            "acsm_standards/fitt_principle_1_20251110_221821.json",
            "acsm_standards/heart_rate_guidelines_0_20251110_221821.json",
            "nsca_standards/periodization_1_20251110_221821.json",
            "nsca_standards/strength_essentials_0_20251110_221821.json"
        ]
    })
    
    recommendations.append({
        "priority": "P2",
        "task": "向量化训练知识到Qdrant",
        "description": "将训练知识文本向量化并存储到Qdrant，支持语义检索",
        "files": [
            "recommendation_decision_tree.md",
            "user_profile_analysis_logic.md",
            "training_knowledge_texts.json"
        ]
    })
    
    recommendations.append({
        "priority": "P2",
        "task": "扩展用户档案支持训练偏好",
        "description": "确保用户档案MCP服务支持所有训练偏好字段",
        "fields": [
            "preferred_training_split",
            "training_location",
            "exercise_preferences",
            "disliked_exercises",
            "periodization_preference"
        ]
    })
    
    print("\n建议任务列表:")
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{i}. [{rec['priority']}] {rec['task']}")
        print(f"   描述: {rec['description']}")
        if 'files' in rec:
            print(f"   文件: {', '.join(rec['files'][:3])}{'...' if len(rec['files']) > 3 else ''}")
        if 'fields' in rec:
            print(f"   字段: {', '.join(rec['fields'])}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("知识覆盖检查工具")
    print("="*60)
    
    try:
        check_neo4j_knowledge()
        check_qdrant_knowledge()
        check_training_knowledge_files()
        generate_recommendations()
        
        print("\n" + "="*60)
        print("✅ 检查完成")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
