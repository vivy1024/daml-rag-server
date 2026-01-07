# -*- coding: utf-8 -*-
"""Neo4j图数据库管理器

提供Neo4j连接管理和CRUD操作
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from contextlib import contextmanager
from neo4j import GraphDatabase, Driver, Session, Transaction
from neo4j.exceptions import ServiceUnavailable, TransactionError
import time

logger = logging.getLogger(__name__)


class Neo4jManager:
    """Neo4j图数据库管理器"""
    
    def __init__(
        self,
        uri: str = "bolt://localhost:7687",
        user: str = "neo4j",
        password: str = "password",
        database: str = "neo4j",
        max_connection_lifetime: int = 3600,
        max_connection_pool_size: int = 50,
        connection_timeout: int = 30
    ):
        """
        初始化Neo4j管理器
        
        Args:
            uri: Neo4j连接URI
            user: 用户名
            password: 密码
            database: 数据库名称
            max_connection_lifetime: 最大连接生命周期（秒）
            max_connection_pool_size: 最大连接池大小
            connection_timeout: 连接超时（秒）
        """
        self.uri = uri
        self.user = user
        self.database = database
        
        # 创建驱动
        self.driver: Driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            max_connection_lifetime=max_connection_lifetime,
            max_connection_pool_size=max_connection_pool_size,
            connection_timeout=connection_timeout
        )
        
        # 测试连接
        self._verify_connectivity()
        
        logger.info(f"✅ Neo4j连接成功: {uri} (database={database})")
    
    def _verify_connectivity(self):
        """验证数据库连接"""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1")
                result.single()
            logger.info("✅ Neo4j连接验证成功")
        except ServiceUnavailable as e:
            logger.error(f"❌ Neo4j连接失败: {e}")
            raise
    
    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            logger.info("🔒 Neo4j连接已关闭")
    
    @contextmanager
    def get_session(self) -> Session:
        """获取会话上下文管理器"""
        session = self.driver.session(database=self.database)
        try:
            yield session
        finally:
            session.close()
    
    def execute_query(
        self,
        query: str,
        parameters: Optional[Dict] = None,
        write: bool = False
    ) -> List[Dict]:
        """
        执行Cypher查询
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
            write: 是否为写操作
        
        Returns:
            查询结果列表
        """
        def _execute(tx):
            result = tx.run(query, parameters or {})
            # 在事务内部消费结果
            return [record.data() for record in result]
        
        with self.get_session() as session:
            if write:
                # Neo4j 5.x使用execute_write而不是write_transaction
                if hasattr(session, 'execute_write'):
                    return session.execute_write(_execute)
                else:
                    return session.write_transaction(_execute)
            else:
                # Neo4j 5.x使用execute_read而不是read_transaction
                if hasattr(session, 'execute_read'):
                    return session.execute_read(_execute)
                else:
                    return session.read_transaction(_execute)
    
    def execute_write(
        self,
        query: str,
        parameters: Optional[Dict] = None
    ) -> List[Dict]:
        """
        执行写操作
        
        Args:
            query: Cypher查询语句
            parameters: 查询参数
        
        Returns:
            操作结果
        """
        def _execute(tx):
            result = tx.run(query, parameters or {})
            # 在事务内部消费结果
            return [record.data() for record in result]
        
        with self.get_session() as session:
            # Neo4j 5.x使用execute_write而不是write_transaction
            if hasattr(session, 'execute_write'):
                return session.execute_write(_execute)
            else:
                # 向后兼容旧版本
                return session.write_transaction(_execute)
    
    # ==================== 节点操作 ====================
    
    def create_node(
        self,
        label: str,
        properties: Dict[str, Any],
        return_node: bool = True
    ) -> Optional[Dict]:
        """
        创建节点
        
        Args:
            label: 节点标签
            properties: 节点属性
            return_node: 是否返回创建的节点
        
        Returns:
            创建的节点（如果return_node=True）
        """
        query = f"""
        CREATE (n:{label} $properties)
        {"RETURN n" if return_node else ""}
        """
        
        result = self.execute_write(query, {"properties": properties})
        
        if return_node and result:
            return dict(result[0]["n"])
        return None
    
    def get_node(
        self,
        label: str,
        properties: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        获取节点
        
        Args:
            label: 节点标签
            properties: 匹配属性
        
        Returns:
            节点数据
        """
        # 构建WHERE子句
        where_clauses = [f"n.{k} = ${k}" for k in properties.keys()]
        where_str = " AND ".join(where_clauses)
        
        query = f"""
        MATCH (n:{label})
        WHERE {where_str}
        RETURN n
        LIMIT 1
        """
        
        result = self.execute_query(query, properties)
        
        if result:
            return dict(result[0]["n"])
        return None
    
    def update_node(
        self,
        label: str,
        match_properties: Dict[str, Any],
        update_properties: Dict[str, Any]
    ) -> bool:
        """
        更新节点
        
        Args:
            label: 节点标签
            match_properties: 匹配属性
            update_properties: 更新属性
        
        Returns:
            是否更新成功
        """
        # 构建WHERE和SET子句
        where_clauses = [f"n.{k} = ${k}" for k in match_properties.keys()]
        where_str = " AND ".join(where_clauses)
        
        set_clauses = [f"n.{k} = $update_{k}" for k in update_properties.keys()]
        set_str = ", ".join(set_clauses)
        
        query = f"""
        MATCH (n:{label})
        WHERE {where_str}
        SET {set_str}
        RETURN count(n) as updated_count
        """
        
        # 合并参数
        params = {**match_properties}
        params.update({f"update_{k}": v for k, v in update_properties.items()})
        
        result = self.execute_write(query, params)
        
        return result[0]["updated_count"] > 0 if result else False
    
    def delete_node(
        self,
        label: str,
        properties: Dict[str, Any],
        detach: bool = True
    ) -> int:
        """
        删除节点
        
        Args:
            label: 节点标签
            properties: 匹配属性
            detach: 是否同时删除关系
        
        Returns:
            删除的节点数量
        """
        # 构建WHERE子句
        where_clauses = [f"n.{k} = ${k}" for k in properties.keys()]
        where_str = " AND ".join(where_clauses)
        
        detach_str = "DETACH " if detach else ""
        
        query = f"""
        MATCH (n:{label})
        WHERE {where_str}
        {detach_str}DELETE n
        RETURN count(n) as deleted_count
        """
        
        result = self.execute_write(query, properties)
        
        return result[0]["deleted_count"] if result else 0
    
    def batch_create_nodes(
        self,
        label: str,
        nodes: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        批量创建节点
        
        Args:
            label: 节点标签
            nodes: 节点列表
            batch_size: 批次大小
        
        Returns:
            创建的节点数量
        """
        total_created = 0
        
        for i in range(0, len(nodes), batch_size):
            batch = nodes[i:i + batch_size]
            
            query = f"""
            UNWIND $batch as node
            CREATE (n:{label})
            SET n = node
            RETURN count(n) as created_count
            """
            
            result = self.execute_write(query, {"batch": batch})
            batch_count = result[0]["created_count"] if result else 0
            total_created += batch_count
            
            logger.info(f"  批次 {i//batch_size + 1}: 创建了 {batch_count} 个节点")
        
        logger.info(f"✅ 批量创建完成: 总共 {total_created} 个节点")
        return total_created
    
    # ==================== 关系操作 ====================
    
    def create_relationship(
        self,
        from_label: str,
        from_properties: Dict[str, Any],
        rel_type: str,
        to_label: str,
        to_properties: Dict[str, Any],
        rel_properties: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        创建关系
        
        Args:
            from_label: 源节点标签
            from_properties: 源节点匹配属性
            rel_type: 关系类型
            to_label: 目标节点标签
            to_properties: 目标节点匹配属性
            rel_properties: 关系属性
        
        Returns:
            是否创建成功
        """
        # 构建WHERE子句
        from_where = " AND ".join([f"a.{k} = $from_{k}" for k in from_properties.keys()])
        to_where = " AND ".join([f"b.{k} = $to_{k}" for k in to_properties.keys()])
        
        # 关系属性
        rel_props_str = ""
        if rel_properties:
            rel_props_str = " $rel_props"
        
        query = f"""
        MATCH (a:{from_label}), (b:{to_label})
        WHERE {from_where} AND {to_where}
        MERGE (a)-[r:{rel_type}{rel_props_str}]->(b)
        RETURN count(r) as created_count
        """
        
        # 合并参数
        params = {}
        params.update({f"from_{k}": v for k, v in from_properties.items()})
        params.update({f"to_{k}": v for k, v in to_properties.items()})
        if rel_properties:
            params["rel_props"] = rel_properties
        
        result = self.execute_write(query, params)
        
        return result[0]["created_count"] > 0 if result else False
    
    def batch_create_relationships(
        self,
        relationships: List[Dict[str, Any]],
        batch_size: int = 1000
    ) -> int:
        """
        批量创建关系
        
        Args:
            relationships: 关系列表，每个关系包含：
                {
                    "from_id": str,
                    "from_label": str,
                    "rel_type": str,
                    "to_id": str,
                    "to_label": str,
                    "properties": dict (optional)
                }
            batch_size: 批次大小
        
        Returns:
            创建的关系数量
        """
        total_created = 0
        
        for i in range(0, len(relationships), batch_size):
            batch = relationships[i:i + batch_size]
            
            query = """
            UNWIND $batch as rel
            MATCH (a), (b)
            WHERE elementId(a) = rel.from_id AND elementId(b) = rel.to_id
            CALL apoc.create.relationship(a, rel.rel_type, rel.properties, b) YIELD rel as r
            RETURN count(r) as created_count
            """
            
            result = self.execute_write(query, {"batch": batch})
            batch_count = result[0]["created_count"] if result else 0
            total_created += batch_count
            
            logger.info(f"  批次 {i//batch_size + 1}: 创建了 {batch_count} 个关系")
        
        logger.info(f"✅ 批量创建关系完成: 总共 {total_created} 个关系")
        return total_created
    
    # ==================== 查询操作 ====================
    
    def get_neighbors(
        self,
        node_id: str,
        direction: str = "both",
        rel_types: Optional[List[str]] = None,
        depth: int = 1
    ) -> List[Dict]:
        """
        获取邻居节点
        
        Args:
            node_id: 节点ID
            direction: 方向 ("in", "out", "both")
            rel_types: 关系类型列表
            depth: 深度
        
        Returns:
            邻居节点列表
        """
        # 确定关系方向
        if direction == "out":
            rel_pattern = "-[r]->"
        elif direction == "in":
            rel_pattern = "<-[r]-"
        else:
            rel_pattern = "-[r]-"
        
        # 关系类型过滤
        rel_type_str = ""
        if rel_types:
            rel_type_str = ":" + "|".join(rel_types)
        
        query = f"""
        MATCH (n){rel_pattern[:3]}{rel_type_str}{rel_pattern[3:]}(neighbor)
        WHERE elementId(n) = $node_id
        RETURN DISTINCT neighbor, type(r) as rel_type, r as relationship
        LIMIT 100
        """
        
        result = self.execute_query(query, {"node_id": node_id})
        
        return result
    
    def find_shortest_path(
        self,
        from_id: str,
        to_id: str,
        max_depth: int = 5
    ) -> Optional[List[Dict]]:
        """
        查找最短路径
        
        Args:
            from_id: 起始节点ID
            to_id: 目标节点ID
            max_depth: 最大深度
        
        Returns:
            路径节点和关系列表
        """
        query = """
        MATCH path = shortestPath((start)-[*..{max_depth}]-(end))
        WHERE elementId(start) = $from_id AND elementId(end) = $to_id
        RETURN [node in nodes(path) | node] as nodes,
               [rel in relationships(path) | rel] as relationships
        """.format(max_depth=max_depth)
        
        result = self.execute_query(query, {
            "from_id": from_id,
            "to_id": to_id
        })
        
        return result[0] if result else None
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取图统计信息
        
        Returns:
            统计信息字典
        """
        stats = {}
        
        # 节点数量
        query = "MATCH (n) RETURN count(n) as node_count"
        result = self.execute_query(query)
        stats["total_nodes"] = result[0]["node_count"]
        
        # 关系数量
        query = "MATCH ()-[r]->() RETURN count(r) as rel_count"
        result = self.execute_query(query)
        stats["total_relationships"] = result[0]["rel_count"]
        
        # 按标签统计节点
        query = """
        MATCH (n)
        RETURN labels(n)[0] as label, count(n) as count
        ORDER BY count DESC
        """
        result = self.execute_query(query)
        stats["nodes_by_label"] = {r["label"]: r["count"] for r in result}
        
        # 按类型统计关系
        query = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        result = self.execute_query(query)
        stats["relationships_by_type"] = {r["type"]: r["count"] for r in result}
        
        return stats
    
    def create_indexes(self):
        """创建常用索引"""
        indexes = [
            "CREATE INDEX exercise_id IF NOT EXISTS FOR (n:Exercise) ON (n.id)",
            "CREATE INDEX muscle_id IF NOT EXISTS FOR (n:Muscle) ON (n.id)",
            "CREATE INDEX food_id IF NOT EXISTS FOR (n:Food) ON (n.id)",
            "CREATE INDEX user_id IF NOT EXISTS FOR (n:User) ON (n.id)",
        ]
        
        for idx_query in indexes:
            try:
                self.execute_write(idx_query)
                logger.info(f"✅ 创建索引: {idx_query[:50]}...")
            except Exception as e:
                logger.warning(f"⚠️ 索引可能已存在: {e}")
        
        logger.info("✅ 索引创建完成")
    
    def __enter__(self):
        """上下文管理器入口"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.close()

