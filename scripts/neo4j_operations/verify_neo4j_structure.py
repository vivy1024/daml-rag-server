#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo4j数据库结构验证脚本
验证真实的节点类型、关系类型和数据完整性
"""

import json
import os
from neo4j import GraphDatabase
from datetime import datetime

# Neo4j连接配置（从环境变量读取或使用默认值）
# 注意：Docker内部地址是 bolt://neo4j:7687，但外部访问需要映射
# 先尝试本地地址，失败后再尝试Docker地址
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'build_body_2024')

# 尝试多个地址
NEO4J_ADDRESSES = [
    ('localhost', 7687, 'bolt://localhost:7687'),
    ('neo4j', 7687, 'bolt://neo4j:7687'),
]

class Neo4jStructureVerifier:
    def __init__(self):
        self.driver = None
        self.stats = {
            'nodes_by_label': {},
            'relationships_by_type': {},
            'total_nodes': 0,
            'total_relationships': 0,
            'sample_data': {},
            'verification_time': datetime.now().isoformat()
        }

    def connect(self):
        """连接数据库（尝试多个地址）"""
        last_error = None

        # 尝试不同的地址
        for host, port, uri in NEO4J_ADDRESSES:
            try:
                print(f"🔌 尝试连接 {uri}...")
                self.driver = GraphDatabase.driver(
                    uri,
                    auth=(NEO4J_USER, NEO4J_PASSWORD) if NEO4J_USER and NEO4J_PASSWORD else None,
                    max_connection_lifetime=30
                )

                # 测试连接
                with self.driver.session() as session:
                    result = session.run("RETURN 1 as test")
                    if result.single()['test'] == 1:
                        print(f"OK 成功连接到 Neo4j: {uri}")
                        return True

            except Exception as e:
                last_error = e
                print(f"WARN  连接 {uri} 失败: {e}")
                continue

        print(f"ERROR 所有连接尝试都失败。最后错误: {last_error}")
        return False

    def verify_structure(self):
        """验证数据库结构"""
        if not self.driver:
            print("ERROR 未连接到数据库")
            return False

        try:
            with self.driver.session() as session:
                # 1. 统计节点总数
                result = session.run("MATCH (n) RETURN count(n) as total")
                self.stats['total_nodes'] = result.single()['total']
                print(f"📊 总节点数: {self.stats['total_nodes']}")

                # 2. 统计各标签节点数量
                print("\n🏷️  节点类型分布:")
                result = session.run("""
                    MATCH (n)
                    RETURN labels(n)[0] as label, count(*) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    label = record['label']
                    count = record['count']
                    self.stats['nodes_by_label'][label] = count
                    print(f"  {label}: {count:,} 个节点")

                # 3. 统计关系总数
                result = session.run("MATCH ()-[r]->() RETURN count(r) as total")
                self.stats['total_relationships'] = result.single()['total']
                print(f"\n🔗 总关系数: {self.stats['total_relationships']:,}")

                # 4. 统计各类型关系数量
                print("\n🔄 关系类型分布:")
                result = session.run("""
                    MATCH ()-[r]->()
                    RETURN type(r) as rel_type, count(*) as count
                    ORDER BY count DESC
                """)
                for record in result:
                    rel_type = record['rel_type']
                    count = record['count']
                    self.stats['relationships_by_type'][rel_type] = count
                    print(f"  {rel_type}: {count:,} 个关系")

                # 5. 检查Exercise节点详细信息
                print("\n💪 Exercise节点详细分析:")
                result = session.run("""
                    MATCH (e:Exercise)
                    RETURN e.name as name, e.difficulty as difficulty,
                           e.equipment as equipment, labels(e) as labels
                    LIMIT 10
                """)
                exercises = []
                for record in result:
                    exercises.append({
                        'name': record['name'],
                        'difficulty': record['difficulty'],
                        'equipment': record['equipment'],
                        'labels': record['labels']
                    })
                self.stats['sample_data']['exercises'] = exercises
                print(f"  样本数据: {len(exercises)} 个练习")

                # 6. 检查Muscle节点详细信息
                print("\n🦴 Muscle节点详细分析:")
                result = session.run("""
                    MATCH (m:Muscle)
                    RETURN m.name as name, m.MEV as MEV, m.MAV as MAV, m.MRV as MRV
                    LIMIT 10
                """)
                muscles = []
                for record in result:
                    muscles.append({
                        'name': record['name'],
                        'MEV': record['MEV'],
                        'MAV': record['MAV'],
                        'MRV': record['MRV']
                    })
                self.stats['sample_data']['muscles'] = muscles
                print(f"  样本数据: {len(muscles)} 个肌肉")

                # 7. 验证关键关系
                print("\n🎯 关键关系验证:")
                relationships_to_check = [
                    ("Exercise", "TARGETS_PRIMARY", "Muscle"),
                    ("Exercise", "TARGETS_SECONDARY", "Muscle"),
                    ("Equipment", "USED_IN", "Exercise"),
                    ("Exercise", "HAS_ALTERNATIVE", "Exercise")
                ]

                for src, rel, dst in relationships_to_check:
                    result = session.run(f"""
                        MATCH (a:{src})-[r:{rel}]->(b:{dst})
                        RETURN count(r) as count
                    """)
                    count = result.single()['count']
                    print(f"  {src} -> {rel} -> {dst}: {count:,} 个关系")

                # 8. 检查数据完整性
                print("\n🔍 数据完整性检查:")

                # 检查孤立节点
                result = session.run("""
                    MATCH (n)
                    WHERE NOT (n)--()
                    RETURN labels(n)[0] as label, count(*) as count
                """)
                isolated = {}
                for record in result:
                    if record['count'] > 0:
                        isolated[record['label']] = record['count']
                if isolated:
                    print(f"  孤立节点: {isolated}")
                else:
                    print("  OK 无孤立节点")

                return True

        except Exception as e:
            print(f"ERROR 验证过程出错: {e}")
            import traceback
            traceback.print_exc()
            return False

    def save_report(self, filename="neo4j_structure_report.json"):
        """保存验证报告"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.stats, f, ensure_ascii=False, indent=2)
            print(f"\n💾 报告已保存到: {filename}")
            return True
        except Exception as e:
            print(f"ERROR 保存报告失败: {e}")
            return False

    def close(self):
        """关闭连接"""
        if self.driver:
            self.driver.close()
            print("🔌 数据库连接已关闭")

def main():
    print("=" * 60)
    print("Neo4j Database Structure Verifier")
    print("=" * 60)

    verifier = Neo4jStructureVerifier()

    try:
        # 连接数据库
        if not verifier.connect():
            return

        # 验证结构
        if verifier.verify_structure():
            # 保存报告
            verifier.save_report("neo4j_structure_report.json")

            # 输出总结
            print("\n" + "=" * 60)
            print("Verification Summary")
            print("=" * 60)
            print(f"Total Nodes: {verifier.stats['total_nodes']:,}")
            print(f"Total Relationships: {verifier.stats['total_relationships']:,}")
            print(f"Node Types: {len(verifier.stats['nodes_by_label'])}")
            print(f"Relationship Types: {len(verifier.stats['relationships_by_type'])}")

        else:
            print("Verification failed")

    finally:
        verifier.close()

if __name__ == "__main__":
    main()
