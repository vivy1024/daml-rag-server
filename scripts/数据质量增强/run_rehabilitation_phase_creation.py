#!/usr/bin/env python3
"""
运行康复阶段节点和关系创建

执行步骤：
1. 创建3个RehabilitationPhase节点
2. 创建REHAB_PROGRESSION关系

作者：薛小川
日期：2025-12-15
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from scripts.data_supplement.rehabilitation_phase_creator import RehabilitationPhaseCreator


async def main():
    """主函数"""
    from dotenv import load_dotenv
    
    # 加载环境变量
    load_dotenv()
    
    # Neo4j配置
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")
    
    print("=" * 80)
    print("🏥 康复阶段节点和关系创建工具")
    print("=" * 80)
    print(f"\nNeo4j URI: {neo4j_uri}")
    print(f"Neo4j User: {neo4j_user}")
    print("\n开始执行...\n")
    
    # 创建创建器
    creator = RehabilitationPhaseCreator(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # 步骤1：创建康复阶段节点
        print("\n" + "=" * 80)
        print("步骤1：创建康复阶段节点")
        print("=" * 80)
        phases_result = await creator.create_phases()
        
        if phases_result.errors:
            print("\n❌ 康复阶段节点创建失败")
            for error in phases_result.errors:
                print(f"   错误: {error}")
            return
        
        print(f"\n✅ 康复阶段节点创建成功")
        print(f"   - 总节点数: {phases_result.total_nodes}")
        print(f"   - 已创建数: {phases_result.updated_nodes}")
        
        # 步骤2：创建康复渐进关系
        print("\n" + "=" * 80)
        print("步骤2：创建康复渐进关系")
        print("=" * 80)
        progressions_result = await creator.create_progressions()
        
        if progressions_result.errors:
            print("\n⚠️ 康复渐进关系创建部分成功")
            for error in progressions_result.errors:
                print(f"   警告: {error}")
        
        print(f"\n✅ 康复渐进关系创建完成")
        print(f"   - 预期关系数: {progressions_result.total_nodes}")
        print(f"   - 已创建数: {progressions_result.updated_nodes}")
        
        # 总结
        print("\n" + "=" * 80)
        print("📊 执行总结")
        print("=" * 80)
        print(f"✅ 康复阶段节点: {phases_result.updated_nodes}/{phases_result.total_nodes}")
        print(f"✅ 康复渐进关系: {progressions_result.updated_nodes}/{progressions_result.total_nodes}")
        print("\n🎉 所有任务执行完成！")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await creator.close()


if __name__ == "__main__":
    asyncio.run(main())
