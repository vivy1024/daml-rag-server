#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建Neo4j缺失的关系

**版本**: v1.0.0
**创建日期**: 2025-12-15
**功能**: 创建TARGETS_PRIMARY、TARGETS_SECONDARY和REQUIRES关系

使用说明:
    # 在Docker容器内运行
    docker exec fitness_daml_rag python scripts/create_missing_relationships.py [--dry-run]

参数:
    --dry-run: 仅预览操作，不实际执行

创建的关系:
1. TARGETS_PRIMARY: Exercise → Muscle (基于primary_muscle_zh字段)
2. TARGETS_SECONDARY: Exercise → Muscle (基于all_muscles_zh字段)
3. REQUIRES: Exercise → Equipment (基于equipment_zh字段)

连接信息:
- Neo4j URI: bolt://fitness_neo4j:7687
- 数据库: neo4j
- 认证: neo4j/build_body_2024
"""

import sys
import os
import argparse
from datetime import datetime
from typing import List, Dict
from neo4j import GraphDatabase

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,fitness_neo4j'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''


class RelationshipCreator:
    """Neo4j关系创建器"""

    def __init__(
        self,
        uri: str = "bolt://fitness_neo4j:7687",
        user: str = "neo4j",
        password: str = "build_body_2024"
    ):
        """初始化连接"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.dry_run = False
        self.stats = {
            "targets_primary_created": 0,
            "targets_secondary_created": 0,
            "requires_created": 0,
            "errors": []
        }

    def close(self):
        """关闭连接"""
        self.driver.close()

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def set_dry_run(self, enabled: bool = True):
        """设置干运行模式"""
        self.dry_run = enabled
        if enabled:
            self.log("🔍 [DRY-RUN MODE] 预览模式，不会实际修改数据", "WARN")

    def execute_query(self, query: str, params: dict = None) -> List[Dict]:
        """执行Cypher查询"""
        if self.dry_run:
            self.log(f"[DRY-RUN] 将执行查询: {query[:100]}...", "DEBUG")
            return []
        
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            self.log(f"❌ 查询执行失败: {str(e)}", "ERROR")
            self.stats["errors"].append(str(e))
            return []

    def check_current_status(self):
        """检查当前关系状态"""
        self.log("\n📊 检查当前关系状态...")
        
        with self.driver.session() as session:
            # 检查各类关系数量
            queries = {
                "TARGETS_PRIMARY": "MATCH ()-[r:TARGETS_PRIMARY]->() RETURN count(r) as count",
                "TARGETS_SECONDARY": "MATCH ()-[r:TARGETS_SECONDARY]->() RETURN count(r) as count",
                "REQUIRES": "MATCH ()-[r:REQUIRES]->() RETURN count(r) as count"
            }
            
            for rel_type, query in queries.items():
                result = session.run(query)
                count = result.single()["count"]
                self.log(f"  {rel_type}: {count} 个关系")
            
            # 检查Exercise和Muscle节点数量
            result = session.run("MATCH (e:Exercise) RETURN count(e) as count")
            exercise_count = result.single()["count"]
            self.log(f"  Exercise节点: {exercise_count} 个")
            
            result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
            muscle_count = result.single()["count"]
            self.log(f"  Muscle节点: {muscle_count} 个")
            
            result = session.run("MATCH (eq:Equipment) RETURN count(eq) as count")
            equipment_count = result.single()["count"]
            self.log(f"  Equipment节点: {equipment_count} 个")

    def create_targets_primary_relations(self) -> int:
        """
        创建TARGETS_PRIMARY关系
        
        基于Exercise.primary_muscle_zh字段匹配Muscle节点
        """
        self.log("\n🔗 [步骤1] 创建TARGETS_PRIMARY关系...")
        
        query = """
        MATCH (e:Exercise)
        WHERE e.primary_muscle_zh IS NOT NULL AND e.primary_muscle_zh <> ''
        WITH e
        MATCH (m:Muscle)
        WHERE m.name_zh = e.primary_muscle_zh
           OR m.name = e.primary_muscle_zh
           OR m.name_en = e.primary_muscle_zh
        MERGE (e)-[r:TARGETS_PRIMARY]->(m)
        RETURN e.name_zh as exercise, m.name_zh as muscle
        """
        
        if self.dry_run:
            # 预览模式：只查询不创建
            preview_query = """
            MATCH (e:Exercise)
            WHERE e.primary_muscle_zh IS NOT NULL AND e.primary_muscle_zh <> ''
            WITH e
            MATCH (m:Muscle)
            WHERE m.name_zh = e.primary_muscle_zh
               OR m.name = e.primary_muscle_zh
               OR m.name_en = e.primary_muscle_zh
            RETURN e.name_zh as exercise, m.name_zh as muscle, e.primary_muscle_zh as target
            LIMIT 10
            """
            
            with self.driver.session() as session:
                results = session.run(preview_query)
                self.log("  预览前10个匹配:")
                for i, record in enumerate(results, 1):
                    self.log(f"    {i}. {record['exercise']} → {record['muscle']} (目标: {record['target']})")
            
            # 统计总数
            count_query = """
            MATCH (e:Exercise)
            WHERE e.primary_muscle_zh IS NOT NULL AND e.primary_muscle_zh <> ''
            WITH e
            MATCH (m:Muscle)
            WHERE m.name_zh = e.primary_muscle_zh
               OR m.name = e.primary_muscle_zh
               OR m.name_en = e.primary_muscle_zh
            RETURN count(*) as total
            """
            with self.driver.session() as session:
                result = session.run(count_query)
                total = result.single()["total"]
                self.log(f"  预计创建: {total} 个TARGETS_PRIMARY关系")
                self.stats["targets_primary_created"] = total
        else:
            results = self.execute_query(query)
            created = len(results)
            self.stats["targets_primary_created"] = created
            
            # 显示前5个示例
            for i, record in enumerate(results[:5], 1):
                self.log(f"  ✅ {i}. {record['exercise']} → {record['muscle']}")
            
            if created > 5:
                self.log(f"  ... 还有 {created - 5} 个关系")
            
            self.log(f"  ✅ 成功创建 {created} 个TARGETS_PRIMARY关系")
        
        return self.stats["targets_primary_created"]

    def create_targets_secondary_relations(self) -> int:
        """
        创建TARGETS_SECONDARY关系
        
        基于Exercise.all_muscles_zh字段匹配Muscle节点
        排除已经是primary_muscle的肌群
        """
        self.log("\n🔗 [步骤2] 创建TARGETS_SECONDARY关系...")
        
        query = """
        MATCH (e:Exercise)
        WHERE e.all_muscles_zh IS NOT NULL AND size(e.all_muscles_zh) > 0
        UNWIND e.all_muscles_zh as muscle_name
        WITH e, muscle_name
        WHERE muscle_name <> e.primary_muscle_zh
        MATCH (m:Muscle)
        WHERE m.name_zh = muscle_name
           OR m.name = muscle_name
           OR m.name_en = muscle_name
        MERGE (e)-[r:TARGETS_SECONDARY]->(m)
        RETURN e.name_zh as exercise, m.name_zh as muscle
        """
        
        if self.dry_run:
            # 预览模式
            preview_query = """
            MATCH (e:Exercise)
            WHERE e.all_muscles_zh IS NOT NULL AND size(e.all_muscles_zh) > 0
            UNWIND e.all_muscles_zh as muscle_name
            WITH e, muscle_name
            WHERE muscle_name <> e.primary_muscle_zh
            MATCH (m:Muscle)
            WHERE m.name_zh = muscle_name
               OR m.name = muscle_name
               OR m.name_en = muscle_name
            RETURN e.name_zh as exercise, m.name_zh as muscle, muscle_name as target
            LIMIT 10
            """
            
            with self.driver.session() as session:
                results = session.run(preview_query)
                self.log("  预览前10个匹配:")
                for i, record in enumerate(results, 1):
                    self.log(f"    {i}. {record['exercise']} → {record['muscle']} (次要: {record['target']})")
            
            # 统计总数
            count_query = """
            MATCH (e:Exercise)
            WHERE e.all_muscles_zh IS NOT NULL AND size(e.all_muscles_zh) > 0
            UNWIND e.all_muscles_zh as muscle_name
            WITH e, muscle_name
            WHERE muscle_name <> e.primary_muscle_zh
            MATCH (m:Muscle)
            WHERE m.name_zh = muscle_name
               OR m.name = muscle_name
               OR m.name_en = muscle_name
            RETURN count(*) as total
            """
            with self.driver.session() as session:
                result = session.run(count_query)
                total = result.single()["total"]
                self.log(f"  预计创建: {total} 个TARGETS_SECONDARY关系")
                self.stats["targets_secondary_created"] = total
        else:
            results = self.execute_query(query)
            created = len(results)
            self.stats["targets_secondary_created"] = created
            
            # 显示前5个示例
            for i, record in enumerate(results[:5], 1):
                self.log(f"  ✅ {i}. {record['exercise']} → {record['muscle']}")
            
            if created > 5:
                self.log(f"  ... 还有 {created - 5} 个关系")
            
            self.log(f"  ✅ 成功创建 {created} 个TARGETS_SECONDARY关系")
        
        return self.stats["targets_secondary_created"]

    def create_requires_relations(self) -> int:
        """
        创建REQUIRES关系
        
        基于Exercise.equipment_zh字段匹配Equipment节点
        """
        self.log("\n🔗 [步骤3] 创建REQUIRES关系...")
        
        query = """
        MATCH (e:Exercise)
        WHERE e.equipment_zh IS NOT NULL AND size(e.equipment_zh) > 0
        UNWIND e.equipment_zh as equipment_name
        WITH e, equipment_name
        MATCH (eq:Equipment)
        WHERE eq.name_zh = equipment_name
           OR eq.name = equipment_name
           OR eq.name_en = equipment_name
        MERGE (e)-[r:REQUIRES]->(eq)
        RETURN e.name_zh as exercise, eq.name_zh as equipment
        """
        
        if self.dry_run:
            # 预览模式
            preview_query = """
            MATCH (e:Exercise)
            WHERE e.equipment_zh IS NOT NULL AND size(e.equipment_zh) > 0
            UNWIND e.equipment_zh as equipment_name
            WITH e, equipment_name
            MATCH (eq:Equipment)
            WHERE eq.name_zh = equipment_name
               OR eq.name = equipment_name
               OR eq.name_en = equipment_name
            RETURN e.name_zh as exercise, eq.name_zh as equipment, equipment_name as target
            LIMIT 10
            """
            
            with self.driver.session() as session:
                results = session.run(preview_query)
                self.log("  预览前10个匹配:")
                for i, record in enumerate(results, 1):
                    self.log(f"    {i}. {record['exercise']} → {record['equipment']} (器械: {record['target']})")
            
            # 统计总数
            count_query = """
            MATCH (e:Exercise)
            WHERE e.equipment_zh IS NOT NULL AND size(e.equipment_zh) > 0
            UNWIND e.equipment_zh as equipment_name
            WITH e, equipment_name
            MATCH (eq:Equipment)
            WHERE eq.name_zh = equipment_name
               OR eq.name = equipment_name
               OR eq.name_en = equipment_name
            RETURN count(*) as total
            """
            with self.driver.session() as session:
                result = session.run(count_query)
                total = result.single()["total"]
                self.log(f"  预计创建: {total} 个REQUIRES关系")
                self.stats["requires_created"] = total
        else:
            results = self.execute_query(query)
            created = len(results)
            self.stats["requires_created"] = created
            
            # 显示前5个示例
            for i, record in enumerate(results[:5], 1):
                self.log(f"  ✅ {i}. {record['exercise']} → {record['equipment']}")
            
            if created > 5:
                self.log(f"  ... 还有 {created - 5} 个关系")
            
            self.log(f"  ✅ 成功创建 {created} 个REQUIRES关系")
        
        return self.stats["requires_created"]

    def verify_results(self):
        """验证创建结果"""
        self.log("\n📊 验证创建结果...")
        
        with self.driver.session() as session:
            # 检查各类关系数量
            queries = {
                "TARGETS_PRIMARY": "MATCH ()-[r:TARGETS_PRIMARY]->() RETURN count(r) as count",
                "TARGETS_SECONDARY": "MATCH ()-[r:TARGETS_SECONDARY]->() RETURN count(r) as count",
                "REQUIRES": "MATCH ()-[r:REQUIRES]->() RETURN count(r) as count"
            }
            
            for rel_type, query in queries.items():
                result = session.run(query)
                count = result.single()["count"]
                self.log(f"  {rel_type}: {count} 个关系")
            
            # 测试查询：查找胸部训练动作及其目标肌群
            self.log("\n🔍 测试查询: 查找胸部训练动作及其目标肌群")
            test_query = """
            MATCH (e:Exercise)-[:TARGETS_PRIMARY]->(m:Muscle)
            WHERE m.name_zh CONTAINS '胸'
            RETURN e.name_zh as exercise, m.name_zh as muscle
            LIMIT 5
            """
            results = session.run(test_query)
            for record in results:
                self.log(f"  - {record['exercise']} → {record['muscle']}")

    def print_summary(self):
        """打印摘要"""
        self.log("\n" + "=" * 60)
        self.log("📋 创建关系摘要")
        self.log("=" * 60)
        self.log(f"✅ TARGETS_PRIMARY: {self.stats['targets_primary_created']} 个")
        self.log(f"✅ TARGETS_SECONDARY: {self.stats['targets_secondary_created']} 个")
        self.log(f"✅ REQUIRES: {self.stats['requires_created']} 个")
        
        total = (
            self.stats['targets_primary_created'] +
            self.stats['targets_secondary_created'] +
            self.stats['requires_created']
        )
        self.log(f"\n📊 总计: {total} 个关系")
        
        if self.stats["errors"]:
            self.log(f"\n❌ 错误: {len(self.stats['errors'])} 个")
            for error in self.stats["errors"][:5]:
                self.log(f"  - {error}")
        
        self.log("=" * 60)
        
        if self.dry_run:
            self.log("\n🔍 [DRY-RUN] 这是预览模式，没有实际修改数据")
            self.log("💡 移除 --dry-run 参数以实际执行创建操作")
        else:
            self.log("\n✅ 关系创建完成！")

    def run(self):
        """执行完整流程"""
        self.log("=" * 60)
        self.log("🚀 开始创建Neo4j缺失的关系")
        self.log("=" * 60)
        
        try:
            # 1. 检查当前状态
            self.check_current_status()
            
            # 2. 创建TARGETS_PRIMARY关系
            self.create_targets_primary_relations()
            
            # 3. 创建TARGETS_SECONDARY关系
            self.create_targets_secondary_relations()
            
            # 4. 创建REQUIRES关系
            self.create_requires_relations()
            
            # 5. 验证结果
            if not self.dry_run:
                self.verify_results()
            
            # 6. 打印摘要
            self.print_summary()
            
        except Exception as e:
            self.log(f"❌ 执行失败: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="创建Neo4j缺失的关系")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="预览模式，不实际修改数据"
    )
    parser.add_argument(
        "--uri",
        default="bolt://fitness_neo4j:7687",
        help="Neo4j连接URI (默认: bolt://fitness_neo4j:7687)"
    )
    parser.add_argument(
        "--user",
        default="neo4j",
        help="Neo4j用户名 (默认: neo4j)"
    )
    parser.add_argument(
        "--password",
        default="build_body_2024",
        help="Neo4j密码 (默认: build_body_2024)"
    )
    
    args = parser.parse_args()
    
    # 创建关系创建器
    creator = RelationshipCreator(
        uri=args.uri,
        user=args.user,
        password=args.password
    )
    
    # 设置干运行模式
    if args.dry_run:
        creator.set_dry_run(enabled=True)
    
    # 执行创建
    creator.run()


if __name__ == "__main__":
    main()
