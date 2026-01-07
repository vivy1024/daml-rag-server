#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
数据库完整性验证脚本

验证Neo4j、Qdrant、Redis、MySQL数据完整性

版本：v1.0.0
创建日期：2025-12-15
"""

import asyncio
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
import redis
import pymysql

# 数据库配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "neo4j123"

QDRANT_HOST = "localhost"
QDRANT_PORT = 6333

REDIS_HOST = "localhost"
REDIS_PORT = 6379

MYSQL_HOST = "localhost"
MYSQL_PORT = 3306
MYSQL_USER = "root"
MYSQL_PASSWORD = "root"
MYSQL_DB = "yuzhen_fitness"

# 预期数据量
EXPECTED_NEO4J_NODES = 3656
EXPECTED_NEO4J_RELATIONSHIPS = 46882
EXPECTED_QDRANT_VECTORS = 3490


def test_neo4j_integrity():
    """验证Neo4j数据完整性"""
    print("\n" + "=" * 80)
    print("测试：Neo4j数据完整性")
    print("=" * 80)
    
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        
        with driver.session() as session:
            # 统计节点数量
            node_result = session.run("MATCH (n) RETURN count(n) as count")
            node_count = node_result.single()["count"]
            
            # 统计关系数量
            rel_result = session.run("MATCH ()-[r]->() RETURN count(r) as count")
            rel_count = rel_result.single()["count"]
            
            # 统计各类型节点
            label_result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            
            print(f"节点统计:")
            print(f"  总节点数: {node_count} (预期: {EXPECTED_NEO4J_NODES})")
            
            for record in label_result:
                print(f"  - {record['label']}: {record['count']}")
            
            print(f"\n关系统计:")
            print(f"  总关系数: {rel_count} (预期: {EXPECTED_NEO4J_RELATIONSHIPS})")
            
            # 验证
            node_ok = abs(node_count - EXPECTED_NEO4J_NODES) < 100  # 允许±100的误差
            rel_ok = abs(rel_count - EXPECTED_NEO4J_RELATIONSHIPS) < 1000  # 允许±1000的误差
            
            if node_ok and rel_ok:
                print(f"✅ Neo4j数据完整性验证通过")
            else:
                print(f"⚠️  Neo4j数据量与预期不符")
            
            driver.close()
            
            return {
                "node_count": node_count,
                "rel_count": rel_count,
                "passed": node_ok and rel_ok
            }
            
    except Exception as e:
        print(f"❌ Neo4j连接失败: {e}")
        return None


def test_qdrant_integrity():
    """验证Qdrant向量数据完整性"""
    print("\n" + "=" * 80)
    print("测试：Qdrant向量数据完整性")
    print("=" * 80)
    
    try:
        client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        
        # 获取所有集合
        collections = client.get_collections().collections
        
        print(f"集合列表:")
        total_vectors = 0
        
        for collection in collections:
            collection_info = client.get_collection(collection.name)
            vector_count = collection_info.points_count
            total_vectors += vector_count
            print(f"  - {collection.name}: {vector_count} 向量")
        
        print(f"\n总向量数: {total_vectors} (预期: {EXPECTED_QDRANT_VECTORS})")
        
        # 验证
        vector_ok = abs(total_vectors - EXPECTED_QDRANT_VECTORS) < 500  # 允许±500的误差
        
        if vector_ok:
            print(f"✅ Qdrant数据完整性验证通过")
        else:
            print(f"⚠️  Qdrant向量数量与预期不符")
        
        return {
            "total_vectors": total_vectors,
            "collections": len(collections),
            "passed": vector_ok
        }
        
    except Exception as e:
        print(f"❌ Qdrant连接失败: {e}")
        return None


def test_redis_integrity():
    """验证Redis缓存功能"""
    print("\n" + "=" * 80)
    print("测试：Redis缓存功能")
    print("=" * 80)
    
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        
        # 测试连接
        r.ping()
        print(f"✅ Redis连接成功")
        
        # 测试读写
        test_key = "test_integrity_check"
        test_value = "test_value_123"
        
        r.set(test_key, test_value, ex=60)
        retrieved_value = r.get(test_key)
        
        if retrieved_value == test_value:
            print(f"✅ Redis读写测试通过")
            r.delete(test_key)
            
            return {
                "connection": True,
                "read_write": True,
                "passed": True
            }
        else:
            print(f"❌ Redis读写测试失败")
            return {
                "connection": True,
                "read_write": False,
                "passed": False
            }
        
    except Exception as e:
        print(f"❌ Redis连接失败: {e}")
        return None


def test_mysql_integrity():
    """验证MySQL用户数据"""
    print("\n" + "=" * 80)
    print("测试：MySQL用户数据")
    print("=" * 80)
    
    try:
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB
        )
        
        cursor = conn.cursor()
        
        # 统计用户数量
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        print(f"用户数量: {user_count}")
        
        # 验证测试用户存在
        cursor.execute("SELECT id, name FROM users WHERE id = 2")
        test_user = cursor.fetchone()
        
        if test_user:
            print(f"✅ 测试用户存在: ID={test_user[0]}, Name={test_user[1]}")
            
            cursor.close()
            conn.close()
            
            return {
                "user_count": user_count,
                "test_user_exists": True,
                "passed": True
            }
        else:
            print(f"⚠️  测试用户不存在")
            
            cursor.close()
            conn.close()
            
            return {
                "user_count": user_count,
                "test_user_exists": False,
                "passed": False
            }
        
    except Exception as e:
        print(f"❌ MySQL连接失败: {e}")
        return None


def main():
    """运行所有数据库完整性测试"""
    print("\n" + "=" * 80)
    print("DAML-RAG数据库完整性验证")
    print("=" * 80)
    
    # 测试1：Neo4j
    neo4j_result = test_neo4j_integrity()
    
    # 测试2：Qdrant
    qdrant_result = test_qdrant_integrity()
    
    # 测试3：Redis
    redis_result = test_redis_integrity()
    
    # 测试4：MySQL
    mysql_result = test_mysql_integrity()
    
    # 总结
    print("\n" + "=" * 80)
    print("数据库完整性验证总结")
    print("=" * 80)
    
    results = {
        "neo4j": neo4j_result,
        "qdrant": qdrant_result,
        "redis": redis_result,
        "mysql": mysql_result
    }
    
    for db_name, result in results.items():
        if result:
            status = "✅ 通过" if result.get('passed', False) else "❌ 未通过"
            print(f"{db_name.upper()}: {status}")
        else:
            print(f"{db_name.upper()}: ❌ 连接失败")
    
    all_passed = all(
        result and result.get('passed', False)
        for result in results.values()
    )
    
    print(f"\n总体结果: {'✅ 所有数据库验证通过' if all_passed else '⚠️  部分数据库验证未通过'}")
    
    return results


if __name__ == "__main__":
    main()
