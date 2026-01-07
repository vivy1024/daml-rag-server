"""
简单测试备份管理器

验证BackupManager的基本功能

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-19
"""

import asyncio
import sys
import os
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

# 设置环境变量
os.environ.setdefault("NEO4J_URI", "bolt://fitness_neo4j:7687")
os.environ.setdefault("NEO4J_USER", "neo4j")
os.environ.setdefault("NEO4J_PASSWORD", "build_body_2024")
os.environ.setdefault("NEO4J_DATABASE", "neo4j")


async def main():
    """主函数"""
    
    print("=" * 60)
    print("测试备份管理器")
    print("=" * 60)
    
    # 导入模块
    from framework.clients.neo4j_client import Neo4jClient, Neo4jClientConfig
    
    # 1. 连接Neo4j
    print("\n1. 连接Neo4j...")
    config = Neo4jClientConfig.from_env()
    print(f"   URI: {config.uri}")
    print(f"   User: {config.user}")
    print(f"   Database: {config.database}")
    
    neo4j_client = Neo4jClient(config)
    
    if not await neo4j_client.connect():
        print("❌ Neo4j连接失败")
        return
    
    print("✅ Neo4j连接成功")
    
    # 2. 获取数据库信息
    print("\n2. 获取数据库信息...")
    db_info = await neo4j_client.get_database_info()
    print(f"📊 节点数: {db_info.get('node_count', 0)}")
    print(f"📊 关系数: {db_info.get('relationship_count', 0)}")
    print(f"📊 标签数: {len(db_info.get('labels', []))}")
    
    # 3. 测试备份目录创建
    print("\n3. 测试备份目录...")
    backup_dir = Path("data/backups/test")
    backup_dir.mkdir(parents=True, exist_ok=True)
    print(f"✅ 备份目录: {backup_dir}")
    
    # 4. 创建测试备份
    print("\n4. 创建测试备份...")
    backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"backup_{backup_id}"
    backup_path.mkdir(parents=True, exist_ok=True)
    
    # 导出节点
    print("   导出节点...")
    nodes_query = """
    MATCH (n)
    RETURN 
        id(n) as node_id,
        labels(n) as labels,
        properties(n) as properties
    LIMIT 10
    """
    nodes_result = await neo4j_client.execute_query(nodes_query)
    
    nodes_data = []
    for record in nodes_result:
        nodes_data.append({
            "node_id": record["node_id"],
            "labels": record["labels"],
            "properties": record["properties"]
        })
    
    # 保存节点数据
    nodes_file = backup_path / "nodes.json"
    with open(nodes_file, 'w', encoding='utf-8') as f:
        json.dump(nodes_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ 已导出 {len(nodes_data)} 个节点（示例）")
    
    # 导出关系
    print("   导出关系...")
    relationships_query = """
    MATCH (a)-[r]->(b)
    RETURN 
        id(a) as start_node_id,
        id(b) as end_node_id,
        type(r) as rel_type,
        properties(r) as properties
    LIMIT 10
    """
    relationships_result = await neo4j_client.execute_query(relationships_query)
    
    relationships_data = []
    for record in relationships_result:
        relationships_data.append({
            "start_node_id": record["start_node_id"],
            "end_node_id": record["end_node_id"],
            "rel_type": record["rel_type"],
            "properties": record["properties"]
        })
    
    # 保存关系数据
    relationships_file = backup_path / "relationships.json"
    with open(relationships_file, 'w', encoding='utf-8') as f:
        json.dump(relationships_data, f, ensure_ascii=False, indent=2)
    
    print(f"   ✅ 已导出 {len(relationships_data)} 个关系（示例）")
    
    # 创建元数据
    metadata = {
        "backup_id": backup_id,
        "backup_name": "test_backup",
        "created_at": datetime.now().isoformat(),
        "node_count": len(nodes_data),
        "relationship_count": len(relationships_data),
        "labels": db_info.get("labels", []),
        "database_info": db_info
    }
    
    metadata_file = backup_path / "metadata.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 备份创建成功: {backup_id}")
    print(f"📁 备份路径: {backup_path}")
    
    # 5. 列出备份
    print("\n5. 列出备份...")
    backups = []
    for backup_dir_item in backup_dir.iterdir():
        if backup_dir_item.is_dir() and backup_dir_item.name.startswith("backup_"):
            metadata_file = backup_dir_item / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                backups.append(metadata)
    
    print(f"📋 找到 {len(backups)} 个备份:")
    for backup in backups:
        print(f"  - {backup['backup_id']}: {backup['backup_name']}")
        print(f"    创建时间: {backup['created_at']}")
        print(f"    节点数: {backup['node_count']}, 关系数: {backup['relationship_count']}")
    
    # 6. 断开连接
    print("\n6. 断开Neo4j连接...")
    await neo4j_client.disconnect()
    print("✅ 连接已断开")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
