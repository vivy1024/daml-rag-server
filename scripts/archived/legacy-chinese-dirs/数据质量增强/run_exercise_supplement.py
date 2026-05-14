#!/usr/bin/env python3
"""
运行Exercise节点数据补充

使用方法：
1. 仅补充基础字段（不使用Ollama）：
   python scripts/data_supplement/run_exercise_supplement.py

2. 使用Ollama生成技术检查点：
   python scripts/data_supplement/run_exercise_supplement.py --use-ollama --batch-size 100
"""

import asyncio
import sys
import os
import argparse
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from src.applications.fitness.data_supplement import DataSupplementManager
from src.framework.clients.neo4j_client import Neo4jClient
from dotenv import load_dotenv


async def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='运行Exercise节点数据补充')
    parser.add_argument('--use-ollama', action='store_true', help='使用Ollama生成技术检查点')
    parser.add_argument('--batch-size', type=int, default=100, help='Ollama批量生成的批次大小')
    args = parser.parse_args()
    
    print("\n" + "=" * 60)
    print("Exercise节点数据补充")
    print("=" * 60)
    print(f"使用Ollama: {'是' if args.use_ollama else '否'}")
    if args.use_ollama:
        print(f"批次大小: {args.batch_size}")
    print("=" * 60)
    
    # 加载环境变量
    load_dotenv()
    
    # 创建Neo4j客户端
    neo4j_client = Neo4jClient()
    await neo4j_client.connect()
    
    try:
        # 获取Neo4j driver
        if not neo4j_client._manager:
            print("❌ Neo4j客户端未正确初始化")
            return 1
        
        neo4j_driver = neo4j_client._manager.driver
        
        # 创建数据补充管理器
        manager = DataSupplementManager(neo4j_driver)
        
        # 执行Exercise节点补充
        print("\n开始执行数据补充...")
        report = await manager.execute_exercise_only()
        
        # 输出报告
        print("\n" + report.generate_summary())
        
        # 保存详细报告到文件
        report_file = "exercise_supplement_report.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\n详细报告已保存到: {report_file}")
        
        # 返回状态码
        return 0 if report.is_successful else 1
        
    finally:
        await neo4j_client.disconnect()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
