"""
测试备份管理器

验证BackupManager的基本功能：
- 创建备份
- 列出备份
- 获取备份信息
- 删除备份

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-19
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from framework.clients.neo4j_client import Neo4jClient, Neo4jClientConfig

# 直接导入BackupManager，避免通过__init__.py导入其他模块
import importlib.util
spec = importlib.util.spec_from_file_location(
    "backup_manager",
    project_root / "src/applications/fitness/data_supplement/backup_manager.py"
)
backup_manager_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup_manager_module)
BackupManager = backup_manager_module.BackupManager


async def test_backup_manager():
    """测试备份管理器"""
    
    print("=" * 60)
    print("测试备份管理器")
    print("=" * 60)
    
    # 1. 创建Neo4j客户端
    print("\n1. 连接Neo4j...")
    config = Neo4jClientConfig.from_env()
    neo4j_client = Neo4jClient(config)
    
    if not await neo4j_client.connect():
        print("❌ Neo4j连接失败")
        return
    
    print("✅ Neo4j连接成功")
    
    # 2. 创建备份管理器
    print("\n2. 初始化备份管理器...")
    backup_manager = BackupManager(
        neo4j_client=neo4j_client,
        backup_dir="data/backups/test"
    )
    print("✅ 备份管理器初始化成功")
    
    # 3. 获取当前数据库信息
    print("\n3. 获取当前数据库信息...")
    db_info = await neo4j_client.get_database_info()
    print(f"📊 节点数: {db_info.get('node_count', 0)}")
    print(f"📊 关系数: {db_info.get('relationship_count', 0)}")
    print(f"📊 标签: {db_info.get('labels', [])}")
    
    # 4. 创建备份
    print("\n4. 创建备份...")
    try:
        backup_id = await backup_manager.create_backup("test_backup")
        print(f"✅ 备份创建成功: {backup_id}")
    except Exception as e:
        print(f"❌ 备份创建失败: {str(e)}")
        await neo4j_client.disconnect()
        return
    
    # 5. 列出所有备份
    print("\n5. 列出所有备份...")
    backups = backup_manager.list_backups()
    print(f"📋 找到 {len(backups)} 个备份:")
    for backup in backups:
        print(f"  - {backup.backup_id}: {backup.backup_name}")
        print(f"    创建时间: {backup.created_at}")
        print(f"    节点数: {backup.node_count}, 关系数: {backup.relationship_count}")
    
    # 6. 获取备份信息
    print(f"\n6. 获取备份信息: {backup_id}...")
    backup_info = backup_manager.get_backup_info(backup_id)
    if backup_info:
        print(f"✅ 备份信息:")
        print(f"  - ID: {backup_info.backup_id}")
        print(f"  - 名称: {backup_info.backup_name}")
        print(f"  - 创建时间: {backup_info.created_at}")
        print(f"  - 节点数: {backup_info.node_count}")
        print(f"  - 关系数: {backup_info.relationship_count}")
        print(f"  - 标签: {backup_info.labels}")
    else:
        print("❌ 获取备份信息失败")
    
    # 7. 测试恢复功能（可选，注释掉以避免清空数据库）
    print("\n7. 测试恢复功能...")
    print("⚠️  跳过恢复测试（避免清空数据库）")
    # try:
    #     success = await backup_manager.restore_backup(backup_id)
    #     if success:
    #         print("✅ 备份恢复成功")
    #     else:
    #         print("❌ 备份恢复失败")
    # except Exception as e:
    #     print(f"❌ 备份恢复失败: {str(e)}")
    
    # 8. 删除测试备份
    print(f"\n8. 删除测试备份: {backup_id}...")
    if backup_manager.delete_backup(backup_id):
        print("✅ 备份删除成功")
    else:
        print("❌ 备份删除失败")
    
    # 9. 断开连接
    print("\n9. 断开Neo4j连接...")
    await neo4j_client.disconnect()
    print("✅ 连接已断开")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_backup_manager())
