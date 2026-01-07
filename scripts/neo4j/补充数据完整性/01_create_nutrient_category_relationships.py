#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建Nutrient→NutrientCategory关系

功能：
- 基于Nutrient节点的category字段创建BELONGS_TO关系
- 连接到对应的NutrientCategory节点

优先级：P3
预期效果：消除NutrientCategory的孤立状态
"""

import os
import sys
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j连接配置
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "your_password")


class NutrientCategoryRelationshipCreator:
    def __init__(self):
        self.driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
        self.stats = {
            "belongs_to_created": 0,
            "errors": []
        }
    
    def close(self):
        self.driver.close()
    
    def log(self, message):
        """打印日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {message}")
    
    def create_belongs_to_relationships(self):
        """创建BELONGS_TO关系"""
        self.log("\n🔗 创建Nutrient→NutrientCategory BELONGS_TO关系...")
        
        with self.driver.session() as session:
            # 查询所有Nutrient节点及其category
            result = session.run("""
                MATCH (n:Nutrient)
                WHERE n.category IS NOT NULL
                RETURN n.name as nutrient_name, n.category as category
            """)
            
            nutrients = list(result)
            self.log(f"  找到 {len(nutrients)} 个Nutrient节点有category字段")
            
            # 为每个Nutrient创建关系
            for nutrient in nutrients:
                try:
                    # 创建BELONGS_TO关系（使用name字段匹配）
                    result = session.run("""
                        MATCH (n:Nutrient {name: $nutrient_name})
                        MATCH (nc:NutrientCategory {name: $category})
                        MERGE (n)-[r:BELONGS_TO]->(nc)
                        RETURN n.name as nutrient_name, nc.name as category_name
                    """, {
                        "nutrient_name": nutrient["nutrient_name"],
                        "category": nutrient["category"]
                    })
                    
                    record = result.single()
                    if record:
                        self.stats["belongs_to_created"] += 1
                        if self.stats["belongs_to_created"] <= 5:
                            self.log(f"    ✅ {record['nutrient_name']} → {record['category_name']}")
                
                except Exception as e:
                    self.stats["errors"].append(f"Nutrient {nutrient['nutrient_name']}: {e}")
            
            if self.stats["belongs_to_created"] > 5:
                self.log(f"    ... 还有 {self.stats['belongs_to_created'] - 5} 个关系")
        
        self.log(f"  ✅ 成功创建 {self.stats['belongs_to_created']} 个BELONGS_TO关系")
    
    def verify_results(self):
        """验证结果"""
        self.log("\n📊 验证结果...")
        
        with self.driver.session() as session:
            # 检查BELONGS_TO关系
            result = session.run("MATCH ()-[r:BELONGS_TO]->() RETURN count(r) as count")
            belongs_to_count = result.single()["count"]
            self.log(f"  BELONGS_TO关系: {belongs_to_count} 个")
            
            # 检查每个NutrientCategory的关系数
            result = session.run("""
                MATCH (nc:NutrientCategory)<-[r:BELONGS_TO]-(n:Nutrient)
                RETURN nc.name as category, count(n) as nutrient_count
                ORDER BY nutrient_count DESC
            """)
            
            self.log("\n  各分类的营养素数量:")
            for record in result:
                self.log(f"    {record['category']}: {record['nutrient_count']} 个")
            
            # 检查孤立的NutrientCategory节点
            result = session.run("""
                MATCH (nc:NutrientCategory)
                WHERE NOT (nc)<-[:BELONGS_TO]-()
                RETURN nc.name as category
            """)
            
            orphaned = list(result)
            if orphaned:
                self.log(f"\n  ⚠️ 仍有 {len(orphaned)} 个孤立的NutrientCategory节点:")
                for record in orphaned:
                    self.log(f"    - {record['category']}")
            else:
                self.log("\n  ✅ 所有NutrientCategory节点都已连接!")
    
    def print_summary(self):
        """打印总结"""
        self.log("\n" + "=" * 60)
        self.log("📊 执行总结")
        self.log("=" * 60)
        self.log(f"✅ BELONGS_TO关系: {self.stats['belongs_to_created']} 个")
        
        if self.stats["errors"]:
            self.log(f"\n⚠️ 错误 ({len(self.stats['errors'])} 个):")
            for error in self.stats["errors"][:5]:
                self.log(f"  - {error}")
            if len(self.stats["errors"]) > 5:
                self.log(f"  ... 还有 {len(self.stats['errors']) - 5} 个错误")
    
    def run(self):
        """执行流程"""
        try:
            self.log("=" * 60)
            self.log("🚀 创建Nutrient→NutrientCategory关系")
            self.log("=" * 60)
            
            # 1. 创建BELONGS_TO关系
            self.create_belongs_to_relationships()
            
            # 2. 验证结果
            self.verify_results()
            
            # 3. 打印总结
            self.print_summary()
            
            self.log("\n✅ 完成!")
        
        except Exception as e:
            self.log(f"\n❌ 执行失败: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            self.close()


if __name__ == "__main__":
    creator = NutrientCategoryRelationshipCreator()
    creator.run()
