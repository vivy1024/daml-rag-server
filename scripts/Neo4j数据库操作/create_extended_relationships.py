#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建Neo4j扩展关系

**版本**: v1.0.0
**创建日期**: 2026-01-05
**功能**: 创建变体关系(VARIATION_OF)、关节关系(INVOLVES_JOINT)

使用说明:
    docker exec fitness_daml_rag python scripts/Neo4j数据库操作/create_extended_relationships.py

创建的关系:
1. VARIATION_OF: Exercise → Exercise (基于variation_of字段)
2. INVOLVES_JOINT: Exercise → Joint (基于joints字段，需要先创建Joint节点)

连接信息:
- Neo4j URI: bolt://fitness_neo4j:7687
- 数据库: neo4j
- 认证: neo4j/build_body_2024
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Set
from neo4j import GraphDatabase

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,fitness_neo4j'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 关节映射（ID -> 名称）- 基于常见健身关节
JOINT_MAPPING = {
    1: {"name_en": "Shoulder", "name_zh": "肩关节"},
    2: {"name_en": "Elbow", "name_zh": "肘关节"},
    3: {"name_en": "Wrist", "name_zh": "腕关节"},
    4: {"name_en": "Hip", "name_zh": "髋关节"},
    5: {"name_en": "Knee", "name_zh": "膝关节"},
    6: {"name_en": "Ankle", "name_zh": "踝关节"},
    7: {"name_en": "Spine", "name_zh": "脊柱"},
    8: {"name_en": "Neck", "name_zh": "颈椎"},
    9: {"name_en": "Core", "name_zh": "核心"},
}


class ExtendedRelationshipCreator:
    """Neo4j扩展关系创建器"""

    def __init__(
        self,
        data_file: str,
        uri: str = "bolt://fitness_neo4j:7687",
        user: str = "neo4j",
        password: str = "build_body_2024"
    ):
        """初始化连接"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.data_file = data_file
        self.exercises = []
        self.stats = {
            "joint_nodes_created": 0,
            "variation_of_created": 0,
            "involves_joint_created": 0,
            "errors": []
        }

    def close(self):
        """关闭连接"""
        self.driver.close()

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_exercises(self):
        """加载Exercise数据"""
        self.log(f"加载数据文件: {self.data_file}")
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.exercises = data.get('enhanced_perfect_exercises', [])
        self.log(f"加载了 {len(self.exercises)} 个Exercise")

    def create_joint_nodes(self):
        """创建Joint节点"""
        self.log("\n🔧 [步骤1] 创建Joint节点...")
        
        with self.driver.session() as session:
            # 先检查是否已存在
            result = session.run("MATCH (j:Joint) RETURN count(j) as count")
            existing = result.single()["count"]
            
            if existing > 0:
                self.log(f"  已存在 {existing} 个Joint节点，跳过创建")
                return
            
            # 创建Joint节点
            for joint_id, joint_info in JOINT_MAPPING.items():
                session.run("""
                    CREATE (j:Joint {
                        id: $id,
                        name_en: $name_en,
                        name_zh: $name_zh,
                        created_at: datetime()
                    })
                """, {
                    "id": joint_id,
                    "name_en": joint_info["name_en"],
                    "name_zh": joint_info["name_zh"]
                })
                self.stats["joint_nodes_created"] += 1
            
            self.log(f"  ✅ 创建了 {self.stats['joint_nodes_created']} 个Joint节点")

    def create_variation_relationships(self):
        """创建VARIATION_OF关系"""
        self.log("\n🔗 [步骤2] 创建VARIATION_OF关系...")
        
        # 收集有variation_of的动作
        variations = [(e['id'], e['variation_of']) 
                      for e in self.exercises 
                      if e.get('variation_of')]
        
        self.log(f"  找到 {len(variations)} 个有变体关系的动作")
        
        with self.driver.session() as session:
            for exercise_id, parent_id in variations:
                try:
                    result = session.run("""
                        MATCH (child:Exercise {id: $child_id})
                        MATCH (parent:Exercise {id: $parent_id})
                        MERGE (child)-[r:VARIATION_OF]->(parent)
                        RETURN child.name_zh as child_name, parent.name_zh as parent_name
                    """, {"child_id": exercise_id, "parent_id": parent_id})
                    
                    record = result.single()
                    if record:
                        self.stats["variation_of_created"] += 1
                        if self.stats["variation_of_created"] <= 5:
                            self.log(f"    ✅ {record['child_name']} → {record['parent_name']}")
                except Exception as e:
                    self.stats["errors"].append(f"VARIATION_OF {exercise_id}->{parent_id}: {e}")
        
        if self.stats["variation_of_created"] > 5:
            self.log(f"    ... 还有 {self.stats['variation_of_created'] - 5} 个关系")
        
        self.log(f"  ✅ 成功创建 {self.stats['variation_of_created']} 个VARIATION_OF关系")

    def create_joint_relationships(self):
        """创建INVOLVES_JOINT关系"""
        self.log("\n🔗 [步骤3] 创建INVOLVES_JOINT关系...")
        
        # 收集有joints的动作
        exercises_with_joints = [(e['id'], e['joints']) 
                                  for e in self.exercises 
                                  if e.get('joints')]
        
        self.log(f"  找到 {len(exercises_with_joints)} 个有关节信息的动作")
        
        with self.driver.session() as session:
            for exercise_id, joint_ids in exercises_with_joints:
                for joint_id in joint_ids:
                    try:
                        result = session.run("""
                            MATCH (e:Exercise {id: $exercise_id})
                            MATCH (j:Joint {id: $joint_id})
                            MERGE (e)-[r:INVOLVES_JOINT]->(j)
                            RETURN e.name_zh as exercise_name, j.name_zh as joint_name
                        """, {"exercise_id": exercise_id, "joint_id": joint_id})
                        
                        record = result.single()
                        if record:
                            self.stats["involves_joint_created"] += 1
                            if self.stats["involves_joint_created"] <= 5:
                                self.log(f"    ✅ {record['exercise_name']} → {record['joint_name']}")
                    except Exception as e:
                        self.stats["errors"].append(f"INVOLVES_JOINT {exercise_id}->{joint_id}: {e}")
        
        if self.stats["involves_joint_created"] > 5:
            self.log(f"    ... 还有 {self.stats['involves_joint_created'] - 5} 个关系")
        
        self.log(f"  ✅ 成功创建 {self.stats['involves_joint_created']} 个INVOLVES_JOINT关系")

    def verify_results(self):
        """验证创建结果"""
        self.log("\n📊 验证创建结果...")
        
        with self.driver.session() as session:
            # 检查Joint节点
            result = session.run("MATCH (j:Joint) RETURN count(j) as count")
            joint_count = result.single()["count"]
            self.log(f"  Joint节点: {joint_count} 个")
            
            # 检查VARIATION_OF关系
            result = session.run("MATCH ()-[r:VARIATION_OF]->() RETURN count(r) as count")
            variation_count = result.single()["count"]
            self.log(f"  VARIATION_OF关系: {variation_count} 个")
            
            # 检查INVOLVES_JOINT关系
            result = session.run("MATCH ()-[r:INVOLVES_JOINT]->() RETURN count(r) as count")
            joint_rel_count = result.single()["count"]
            self.log(f"  INVOLVES_JOINT关系: {joint_rel_count} 个")
            
            # 测试查询
            self.log("\n🔍 测试查询: 查找涉及肩关节的动作")
            result = session.run("""
                MATCH (e:Exercise)-[:INVOLVES_JOINT]->(j:Joint {name_zh: '肩关节'})
                RETURN e.name_zh as exercise
                LIMIT 5
            """)
            for record in result:
                self.log(f"    - {record['exercise']}")

    def print_summary(self):
        """打印摘要"""
        self.log("\n" + "=" * 60)
        self.log("📋 扩展关系创建摘要")
        self.log("=" * 60)
        self.log(f"✅ Joint节点: {self.stats['joint_nodes_created']} 个")
        self.log(f"✅ VARIATION_OF: {self.stats['variation_of_created']} 个")
        self.log(f"✅ INVOLVES_JOINT: {self.stats['involves_joint_created']} 个")
        
        if self.stats["errors"]:
            self.log(f"\n❌ 错误: {len(self.stats['errors'])} 个")
            for error in self.stats["errors"][:5]:
                self.log(f"  - {error}")
        
        self.log("=" * 60)
        self.log("\n✅ 扩展关系创建完成！")

    def run(self):
        """执行完整流程"""
        self.log("=" * 60)
        self.log("🚀 开始创建Neo4j扩展关系")
        self.log("=" * 60)
        
        try:
            # 1. 加载数据
            self.load_exercises()
            
            # 2. 创建Joint节点
            self.create_joint_nodes()
            
            # 3. 创建VARIATION_OF关系
            self.create_variation_relationships()
            
            # 4. 创建INVOLVES_JOINT关系
            self.create_joint_relationships()
            
            # 5. 验证结果
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
    parser = argparse.ArgumentParser(description="创建Neo4j扩展关系")
    parser.add_argument(
        "--data-file",
        default="/app/data/enhanced_perfect_exercises_dataset.json",
        help="数据文件路径"
    )
    parser.add_argument(
        "--uri",
        default="bolt://fitness_neo4j:7687",
        help="Neo4j连接URI"
    )
    
    args = parser.parse_args()
    
    creator = ExtendedRelationshipCreator(
        data_file=args.data_file,
        uri=args.uri
    )
    creator.run()


if __name__ == "__main__":
    main()
