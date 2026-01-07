"""
备份管理器

负责Neo4j数据库的备份和恢复操作。
支持创建备份、恢复备份、列出备份和删除备份。

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2025-12-19
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from pathlib import Path

from ....framework.clients.neo4j_client import Neo4jClient


logger = logging.getLogger(__name__)


@dataclass
class BackupInfo:
    """备份信息"""
    backup_id: str
    backup_name: str
    created_at: str
    backup_path: str
    node_count: int
    relationship_count: int
    labels: List[str]
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)


class BackupManager:
    """
    备份管理器
    
    负责Neo4j数据库的备份和恢复操作。
    使用Cypher查询导出/导入数据，而不是依赖Neo4j的dump/restore命令。
    """
    
    def __init__(
        self,
        neo4j_client: Neo4jClient,
        backup_dir: str = "data/backups"
    ):
        """
        初始化备份管理器
        
        Args:
            neo4j_client: Neo4j客户端
            backup_dir: 备份目录路径
        """
        self.neo4j_client = neo4j_client
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"✅ 备份管理器已初始化，备份目录: {self.backup_dir}")
    
    async def create_backup(self, backup_name: str) -> str:
        """
        创建数据库备份
        
        使用Cypher查询导出所有节点和关系到JSON文件。
        
        Args:
            backup_name: 备份名称
            
        Returns:
            str: 备份ID（时间戳格式）
            
        Raises:
            RuntimeError: 备份失败时抛出
        """
        try:
            # 生成备份ID（时间戳）
            backup_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"backup_{backup_id}"
            backup_path.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"🔄 开始创建备份: {backup_name} (ID: {backup_id})")
            
            # 1. 导出所有节点
            logger.info("📦 导出节点数据...")
            nodes_query = """
            MATCH (n)
            RETURN 
                elementId(n) as node_id,
                labels(n) as labels,
                properties(n) as properties
            """
            nodes_result = await self.neo4j_client.execute_query(nodes_query)
            
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
            
            logger.info(f"✅ 已导出 {len(nodes_data)} 个节点")
            
            # 2. 导出所有关系
            logger.info("🔗 导出关系数据...")
            relationships_query = """
            MATCH (a)-[r]->(b)
            RETURN 
                elementId(a) as start_node_id,
                elementId(b) as end_node_id,
                type(r) as rel_type,
                properties(r) as properties
            """
            relationships_result = await self.neo4j_client.execute_query(relationships_query)
            
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
            
            logger.info(f"✅ 已导出 {len(relationships_data)} 个关系")
            
            # 3. 获取数据库统计信息
            db_info = await self.neo4j_client.get_database_info()
            
            # 4. 创建备份元数据
            metadata = {
                "backup_id": backup_id,
                "backup_name": backup_name,
                "created_at": datetime.now().isoformat(),
                "node_count": len(nodes_data),
                "relationship_count": len(relationships_data),
                "labels": db_info.get("labels", []),
                "relationship_types": db_info.get("relationship_types", []),
                "database_info": db_info
            }
            
            # 保存元数据
            metadata_file = backup_path / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ 备份创建成功: {backup_id}")
            logger.info(f"📁 备份路径: {backup_path}")
            logger.info(f"📊 节点数: {len(nodes_data)}, 关系数: {len(relationships_data)}")
            
            return backup_id
            
        except Exception as e:
            logger.error(f"❌ 创建备份失败: {str(e)}")
            raise RuntimeError(f"创建备份失败: {str(e)}")
    
    async def restore_backup(self, backup_id: str) -> bool:
        """
        恢复数据库备份
        
        从备份文件恢复所有节点和关系。
        注意：这会清空当前数据库！
        
        Args:
            backup_id: 备份ID
            
        Returns:
            bool: 恢复是否成功
            
        Raises:
            RuntimeError: 恢复失败时抛出
        """
        try:
            backup_path = self.backup_dir / f"backup_{backup_id}"
            
            if not backup_path.exists():
                raise RuntimeError(f"备份不存在: {backup_id}")
            
            logger.info(f"🔄 开始恢复备份: {backup_id}")
            
            # 1. 读取元数据
            metadata_file = backup_path / "metadata.json"
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            logger.info(f"📋 备份信息: {metadata['backup_name']}")
            logger.info(f"📅 创建时间: {metadata['created_at']}")
            logger.info(f"📊 节点数: {metadata['node_count']}, 关系数: {metadata['relationship_count']}")
            
            # 2. 清空当前数据库（警告：危险操作！）
            logger.warning("⚠️  正在清空当前数据库...")
            clear_query = "MATCH (n) DETACH DELETE n"
            await self.neo4j_client.execute_query(clear_query)
            logger.info("✅ 数据库已清空")
            
            # 3. 读取节点数据
            nodes_file = backup_path / "nodes.json"
            with open(nodes_file, 'r', encoding='utf-8') as f:
                nodes_data = json.load(f)
            
            # 4. 恢复节点（批量创建）
            logger.info(f"📦 恢复 {len(nodes_data)} 个节点...")
            
            # 创建节点ID映射（旧ID -> 新ID）
            node_id_mapping = {}
            
            for node in nodes_data:
                old_id = node["node_id"]
                labels = ":".join(node["labels"])
                properties = node["properties"]
                
                # 构建属性字符串
                props_list = []
                for key, value in properties.items():
                    if isinstance(value, str):
                        props_list.append(f"{key}: '{value}'")
                    elif isinstance(value, bool):
                        props_list.append(f"{key}: {str(value).lower()}")
                    elif isinstance(value, (int, float)):
                        props_list.append(f"{key}: {value}")
                    elif isinstance(value, list):
                        # 处理列表
                        list_str = str(value).replace("'", '"')
                        props_list.append(f"{key}: {list_str}")
                    elif value is None:
                        props_list.append(f"{key}: null")
                
                props_str = ", ".join(props_list)
                
                # 创建节点
                create_query = f"CREATE (n:{labels} {{{props_str}}}) RETURN elementId(n) as new_id"
                result = await self.neo4j_client.execute_query(create_query)
                
                if result:
                    new_id = result[0]["new_id"]
                    node_id_mapping[old_id] = new_id
            
            logger.info(f"✅ 已恢复 {len(node_id_mapping)} 个节点")
            
            # 5. 读取关系数据
            relationships_file = backup_path / "relationships.json"
            with open(relationships_file, 'r', encoding='utf-8') as f:
                relationships_data = json.load(f)
            
            # 6. 恢复关系
            logger.info(f"🔗 恢复 {len(relationships_data)} 个关系...")
            
            restored_count = 0
            for rel in relationships_data:
                old_start_id = rel["start_node_id"]
                old_end_id = rel["end_node_id"]
                rel_type = rel["rel_type"]
                properties = rel["properties"]
                
                # 获取新的节点ID
                new_start_id = node_id_mapping.get(old_start_id)
                new_end_id = node_id_mapping.get(old_end_id)
                
                if new_start_id is None or new_end_id is None:
                    logger.warning(f"⚠️  跳过关系（节点不存在）: {old_start_id} -> {old_end_id}")
                    continue
                
                # 构建属性字符串
                if properties:
                    props_list = []
                    for key, value in properties.items():
                        if isinstance(value, str):
                            props_list.append(f"{key}: '{value}'")
                        elif isinstance(value, bool):
                            props_list.append(f"{key}: {str(value).lower()}")
                        elif isinstance(value, (int, float)):
                            props_list.append(f"{key}: {value}")
                        elif value is None:
                            props_list.append(f"{key}: null")
                    
                    props_str = ", ".join(props_list)
                    create_rel_query = f"""
                    MATCH (a), (b)
                    WHERE elementId(a) = '{new_start_id}' AND elementId(b) = '{new_end_id}'
                    CREATE (a)-[r:{rel_type} {{{props_str}}}]->(b)
                    """
                else:
                    create_rel_query = f"""
                    MATCH (a), (b)
                    WHERE elementId(a) = '{new_start_id}' AND elementId(b) = '{new_end_id}'
                    CREATE (a)-[r:{rel_type}]->(b)
                    """
                
                await self.neo4j_client.execute_query(create_rel_query)
                restored_count += 1
            
            logger.info(f"✅ 已恢复 {restored_count} 个关系")
            
            # 7. 验证恢复结果
            logger.info("🔍 验证恢复结果...")
            db_info = await self.neo4j_client.get_database_info()
            
            logger.info(f"📊 当前数据库状态:")
            logger.info(f"  - 节点数: {db_info.get('node_count', 0)}")
            logger.info(f"  - 关系数: {db_info.get('relationship_count', 0)}")
            logger.info(f"  - 标签: {db_info.get('labels', [])}")
            
            # 检查数据完整性
            if db_info.get('node_count', 0) != metadata['node_count']:
                logger.warning(f"⚠️  节点数不匹配: 预期 {metadata['node_count']}, 实际 {db_info.get('node_count', 0)}")
            
            if db_info.get('relationship_count', 0) != metadata['relationship_count']:
                logger.warning(f"⚠️  关系数不匹配: 预期 {metadata['relationship_count']}, 实际 {db_info.get('relationship_count', 0)}")
            
            logger.info(f"✅ 备份恢复成功: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 恢复备份失败: {str(e)}")
            raise RuntimeError(f"恢复备份失败: {str(e)}")
    
    def list_backups(self) -> List[BackupInfo]:
        """
        列出所有备份
        
        Returns:
            List[BackupInfo]: 备份信息列表
        """
        backups = []
        
        try:
            # 遍历备份目录
            for backup_dir in self.backup_dir.iterdir():
                if not backup_dir.is_dir() or not backup_dir.name.startswith("backup_"):
                    continue
                
                # 读取元数据
                metadata_file = backup_dir / "metadata.json"
                if not metadata_file.exists():
                    logger.warning(f"⚠️  备份缺少元数据文件: {backup_dir.name}")
                    continue
                
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
                
                backup_info = BackupInfo(
                    backup_id=metadata["backup_id"],
                    backup_name=metadata["backup_name"],
                    created_at=metadata["created_at"],
                    backup_path=str(backup_dir),
                    node_count=metadata["node_count"],
                    relationship_count=metadata["relationship_count"],
                    labels=metadata.get("labels", []),
                    metadata=metadata
                )
                
                backups.append(backup_info)
            
            # 按创建时间排序（最新的在前）
            backups.sort(key=lambda x: x.created_at, reverse=True)
            
            logger.info(f"📋 找到 {len(backups)} 个备份")
            
        except Exception as e:
            logger.error(f"❌ 列出备份失败: {str(e)}")
        
        return backups
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        删除备份
        
        Args:
            backup_id: 备份ID
            
        Returns:
            bool: 删除是否成功
        """
        try:
            backup_path = self.backup_dir / f"backup_{backup_id}"
            
            if not backup_path.exists():
                logger.warning(f"⚠️  备份不存在: {backup_id}")
                return False
            
            # 删除备份目录及其所有文件
            import shutil
            shutil.rmtree(backup_path)
            
            logger.info(f"✅ 已删除备份: {backup_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 删除备份失败: {str(e)}")
            return False
    
    def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """
        获取备份信息
        
        Args:
            backup_id: 备份ID
            
        Returns:
            Optional[BackupInfo]: 备份信息，如果不存在则返回None
        """
        try:
            backup_path = self.backup_dir / f"backup_{backup_id}"
            
            if not backup_path.exists():
                return None
            
            metadata_file = backup_path / "metadata.json"
            if not metadata_file.exists():
                return None
            
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
            
            return BackupInfo(
                backup_id=metadata["backup_id"],
                backup_name=metadata["backup_name"],
                created_at=metadata["created_at"],
                backup_path=str(backup_path),
                node_count=metadata["node_count"],
                relationship_count=metadata["relationship_count"],
                labels=metadata.get("labels", []),
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ 获取备份信息失败: {str(e)}")
            return None
