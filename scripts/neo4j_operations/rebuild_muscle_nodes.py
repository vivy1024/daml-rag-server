#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
重建Neo4j Muscle节点

**版本**: v1.0.0
**创建日期**: 2026-01-05
**功能**: 
1. 删除旧的Muscle节点（保留训练数据）
2. 从Exercise的muscles_tree创建新的Muscle节点
3. 建立肌肉层级关系 (PART_OF)
4. 重建Exercise与Muscle的关系

使用说明:
    docker exec fitness_daml_rag python scripts/Neo4j数据库操作/rebuild_muscle_nodes.py
"""

import sys
import os
import json
import argparse
from datetime import datetime
from typing import List, Dict, Set, Tuple
from neo4j import GraphDatabase

os.environ['NO_PROXY'] = 'localhost,127.0.0.1,fitness_neo4j'

class MuscleNodeRebuilder:
    """Muscle节点重建器"""

    def __init__(
        self,
        data_file: str,
        uri: str = "bolt://fitness_neo4j:7687",
        user: str = "neo4j",
        password: str = "build_body_2024"
    ):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.data_file = data_file
        self.exercises = []
        self.muscles = {}  # id -> muscle_info
        self.parent_relations = []  # (child_id, parent_id)
        self.old_muscle_data = {}  # 保存旧节点的训练数据
        self.stats = {
            "old_muscles_backed_up": 0,
            "new_muscles_created": 0,
            "part_of_relations": 0,
            "targets_primary_rebuilt": 0,
            "targets_secondary_rebuilt": 0,
            "errors": []
        }

    def close(self):
        self.driver.close()

    def log(self, message: str, level: str = "INFO"):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def load_exercises(self):
        """加载Exercise数据"""
        self.log(f"加载数据文件: {self.data_file}")
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.exercises = data.get('enhanced_perfect_exercises', [])
        self.log(f"加载了 {len(self.exercises)} 个Exercise")

    def extract_muscles_from_tree(self):
        """从muscles_tree提取所有肌肉信息"""
        self.log("\n📊 从muscles_tree提取肌肉信息...")
        
        for e in self.exercises:
            tree = e.get('muscles_tree') or []
            for m in tree:
                if not m:
                    continue
                muscle_id = m.get('id')
                if muscle_id and muscle_id not in self.muscles:
                    self.muscles[muscle_id] = {
                        'id': muscle_id,
                        'name_en': m.get('name'),
                        'name_zh': m.get('name_zh'),
                        'scientific_name': m.get('scientific_name'),
                        'level': m.get('level', 0),
                        'parent_id': m.get('parent')
                    }
                if m.get('parent'):
                    self.parent_relations.append((muscle_id, m.get('parent')))
        
        self.parent_relations = list(set(self.parent_relations))
        self.log(f"  提取了 {len(self.muscles)} 个肌肉")
        self.log(f"  提取了 {len(self.parent_relations)} 个层级关系")

    def backup_old_muscle_data(self):
        """备份旧Muscle节点的训练数据（MEV/MAV/MRV等）"""
        self.log("\n💾 备份旧Muscle节点的训练数据...")
        
        with self.driver.session() as session:
            result = session.run("""
                MATCH (m:Muscle)
                RETURN m.name_zh as name_zh, m.name_en as name_en,
                       m.mev as mev, m.mav as mav, m.mrv as mrv,
                       m.recovery_days as recovery_days,
                       m.optimal_frequency as optimal_frequency,
                       m.description as description
            """)
            
            for r in result:
                key = r["name_zh"] or r["name_en"]
                if key:
                    self.old_muscle_data[key] = {
                        'mev': r["mev"],
                        'mav': r["mav"],
                        'mrv': r["mrv"],
                        'recovery_days': r["recovery_days"],
                        'optimal_frequency': r["optimal_frequency"],
                        'description': r["description"]
                    }
                    self.stats["old_muscles_backed_up"] += 1
        
        self.log(f"  备份了 {self.stats['old_muscles_backed_up']} 个旧节点的数据")

    def delete_old_muscles(self):
        """删除旧的Muscle节点和相关关系"""
        self.log("\n🗑️ 删除旧Muscle节点...")
        
        with self.driver.session() as session:
            # 统计
            result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
            old_count = result.single()["count"]
            
            # 删除关系和节点
            session.run("MATCH (m:Muscle) DETACH DELETE m")
            
            self.log(f"  删除了 {old_count} 个旧Muscle节点")

    def create_new_muscle_nodes(self):
        """创建新的Muscle节点"""
        self.log("\n🔧 创建新Muscle节点...")
        
        with self.driver.session() as session:
            for muscle_id, muscle in self.muscles.items():
                # 尝试从备份中恢复训练数据
                old_data = self.old_muscle_data.get(muscle['name_zh']) or \
                           self.old_muscle_data.get(muscle['name_en']) or {}
                
                session.run("""
                    CREATE (m:Muscle {
                        id: $id,
                        name_zh: $name_zh,
                        name_en: $name_en,
                        scientific_name: $scientific_name,
                        level: $level,
                        mev: $mev,
                        mav: $mav,
                        mrv: $mrv,
                        recovery_days: $recovery_days,
                        optimal_frequency: $optimal_frequency,
                        description: $description,
                        created_at: datetime()
                    })
                """, {
                    'id': muscle_id,
                    'name_zh': muscle['name_zh'],
                    'name_en': muscle['name_en'],
                    'scientific_name': muscle['scientific_name'],
                    'level': muscle['level'],
                    'mev': old_data.get('mev'),
                    'mav': old_data.get('mav'),
                    'mrv': old_data.get('mrv'),
                    'recovery_days': old_data.get('recovery_days'),
                    'optimal_frequency': old_data.get('optimal_frequency'),
                    'description': old_data.get('description')
                })
                self.stats["new_muscles_created"] += 1
        
        self.log(f"  创建了 {self.stats['new_muscles_created']} 个新Muscle节点")

    def create_muscle_hierarchy(self):
        """创建肌肉层级关系 (PART_OF)"""
        self.log("\n🔗 创建肌肉层级关系 (PART_OF)...")
        
        with self.driver.session() as session:
            for child_id, parent_id in self.parent_relations:
                result = session.run("""
                    MATCH (child:Muscle {id: $child_id})
                    MATCH (parent:Muscle {id: $parent_id})
                    MERGE (child)-[r:PART_OF]->(parent)
                    RETURN child.name_zh as child, parent.name_zh as parent
                """, {'child_id': child_id, 'parent_id': parent_id})
                
                record = result.single()
                if record:
                    self.stats["part_of_relations"] += 1
                    if self.stats["part_of_relations"] <= 5:
                        self.log(f"    {record['child']} -> {record['parent']}")
        
        if self.stats["part_of_relations"] > 5:
            self.log(f"    ... 还有 {self.stats['part_of_relations'] - 5} 个关系")
        self.log(f"  创建了 {self.stats['part_of_relations']} 个PART_OF关系")

    def rebuild_exercise_muscle_relations(self):
        """重建Exercise与Muscle的关系"""
        self.log("\n🔗 重建Exercise-Muscle关系...")
        
        with self.driver.session() as session:
            # TARGETS_PRIMARY - 基于 primary_muscle_zh
            self.log("  [1/2] 创建TARGETS_PRIMARY关系...")
            result = session.run("""
                MATCH (e:Exercise)
                WHERE e.primary_muscle_zh IS NOT NULL AND e.primary_muscle_zh <> ''
                WITH e
                MATCH (m:Muscle)
                WHERE m.name_zh = e.primary_muscle_zh
                MERGE (e)-[r:TARGETS_PRIMARY]->(m)
                RETURN count(r) as count
            """)
            self.stats["targets_primary_rebuilt"] = result.single()["count"]
            self.log(f"    创建了 {self.stats['targets_primary_rebuilt']} 个TARGETS_PRIMARY关系")
            
            # TARGETS_SECONDARY - 基于 all_muscles_zh (排除primary)
            self.log("  [2/2] 创建TARGETS_SECONDARY关系...")
            result = session.run("""
                MATCH (e:Exercise)
                WHERE e.all_muscles_zh IS NOT NULL AND size(e.all_muscles_zh) > 0
                UNWIND e.all_muscles_zh as muscle_name
                WITH e, muscle_name
                WHERE muscle_name <> e.primary_muscle_zh
                MATCH (m:Muscle)
                WHERE m.name_zh = muscle_name
                MERGE (e)-[r:TARGETS_SECONDARY]->(m)
                RETURN count(r) as count
            """)
            self.stats["targets_secondary_rebuilt"] = result.single()["count"]
            self.log(f"    创建了 {self.stats['targets_secondary_rebuilt']} 个TARGETS_SECONDARY关系")

    def verify_results(self):
        """验证结果"""
        self.log("\n📊 验证结果...")
        
        with self.driver.session() as session:
            # Muscle节点
            result = session.run("MATCH (m:Muscle) RETURN count(m) as count")
            muscle_count = result.single()["count"]
            self.log(f"  Muscle节点: {muscle_count} 个")
            
            # 按level统计
            result = session.run("""
                MATCH (m:Muscle)
                RETURN m.level as level, count(m) as count
                ORDER BY level
            """)
            for r in result:
                self.log(f"    Level {r['level']}: {r['count']} 个")
            
            # PART_OF关系
            result = session.run("MATCH ()-[r:PART_OF]->() RETURN count(r) as count")
            part_of_count = result.single()["count"]
            self.log(f"  PART_OF关系: {part_of_count} 个")
            
            # TARGETS_PRIMARY关系
            result = session.run("MATCH ()-[r:TARGETS_PRIMARY]->() RETURN count(r) as count")
            primary_count = result.single()["count"]
            self.log(f"  TARGETS_PRIMARY关系: {primary_count} 个")
            
            # TARGETS_SECONDARY关系
            result = session.run("MATCH ()-[r:TARGETS_SECONDARY]->() RETURN count(r) as count")
            secondary_count = result.single()["count"]
            self.log(f"  TARGETS_SECONDARY关系: {secondary_count} 个")
            
            # 测试查询
            self.log("\n🔍 测试查询: 胸肌的子肌群")
            result = session.run("""
                MATCH (child:Muscle)-[:PART_OF]->(parent:Muscle {name_zh: '胸肌'})
                RETURN child.name_zh as name
            """)
            for r in result:
                self.log(f"    - {r['name']}")

    def print_summary(self):
        """打印摘要"""
        self.log("\n" + "=" * 60)
        self.log("📋 Muscle节点重建摘要")
        self.log("=" * 60)
        self.log(f"✅ 备份旧数据: {self.stats['old_muscles_backed_up']} 个")
        self.log(f"✅ 新Muscle节点: {self.stats['new_muscles_created']} 个")
        self.log(f"✅ PART_OF关系: {self.stats['part_of_relations']} 个")
        self.log(f"✅ TARGETS_PRIMARY: {self.stats['targets_primary_rebuilt']} 个")
        self.log(f"✅ TARGETS_SECONDARY: {self.stats['targets_secondary_rebuilt']} 个")
        
        if self.stats["errors"]:
            self.log(f"\n❌ 错误: {len(self.stats['errors'])} 个")
        
        self.log("=" * 60)
        self.log("\n✅ Muscle节点重建完成！")

    def run(self):
        """执行完整流程"""
        self.log("=" * 60)
        self.log("🚀 开始重建Neo4j Muscle节点")
        self.log("=" * 60)
        
        try:
            # 1. 加载数据
            self.load_exercises()
            
            # 2. 提取肌肉信息
            self.extract_muscles_from_tree()
            
            # 3. 备份旧数据
            self.backup_old_muscle_data()
            
            # 4. 删除旧节点
            self.delete_old_muscles()
            
            # 5. 创建新节点
            self.create_new_muscle_nodes()
            
            # 6. 创建层级关系
            self.create_muscle_hierarchy()
            
            # 7. 重建Exercise-Muscle关系
            self.rebuild_exercise_muscle_relations()
            
            # 8. 验证结果
            self.verify_results()
            
            # 9. 打印摘要
            self.print_summary()
            
        except Exception as e:
            self.log(f"❌ 执行失败: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description="重建Neo4j Muscle节点")
    parser.add_argument(
        "--data-file",
        default="/app/data/enhanced_perfect_exercises_dataset.json",
        help="数据文件路径"
    )
    args = parser.parse_args()
    
    rebuilder = MuscleNodeRebuilder(data_file=args.data_file)
    rebuilder.run()


if __name__ == "__main__":
    main()
