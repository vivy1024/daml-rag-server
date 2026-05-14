#!/usr/bin/env python3
"""
运行InjuryType节点数据补充

执行方式：
1. 在Docker容器内运行：
   docker exec fitness_daml_rag python scripts/data_supplement/run_injury_type_supplement.py

2. 本地运行（需要配置.env）：
   python scripts/data_supplement/run_injury_type_supplement.py

作者：薛小川
日期：2025-12-15
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from scripts.data_supplement.injury_type_supplementer import InjuryTypeSupplementer
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


async def main():
    """主函数"""
    print("=" * 60)
    print("InjuryType节点数据补充脚本")
    print("=" * 60)
    
    # Neo4j配置（Docker容器内）
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://fitness_neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "build_body_2024")
    
    print(f"\n连接配置:")
    print(f"  Neo4j URI: {neo4j_uri}")
    print(f"  Neo4j User: {neo4j_user}")
    print(f"  Neo4j Password: {'*' * len(neo4j_password)}")
    
    # 创建补充器
    supplementer = InjuryTypeSupplementer(neo4j_uri, neo4j_user, neo4j_password)
    
    try:
        # 执行补充
        result = await supplementer.supplement()
        
        # 输出结果
        print("\n" + "=" * 60)
        print("📊 最终结果")
        print("=" * 60)
        print(f"总节点数: {result.total_nodes}")
        print(f"已更新节点数: {result.updated_nodes}")
        print(f"错误数量: {len(result.errors)}")
        
        if result.errors:
            print("\n错误详情:")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.updated_nodes == result.total_nodes:
            print("\n✅ 所有InjuryType节点已成功补充severity_level字段")
        else:
            print(f"\n⚠️ 部分节点未更新: {result.total_nodes - result.updated_nodes} 个")
        
        return 0 if not result.errors else 1
        
    except Exception as e:
        print(f"\n❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        await supplementer.close()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
