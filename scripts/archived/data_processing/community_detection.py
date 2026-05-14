#!/usr/bin/env python3
"""
社区检测脚本 - 基于Exercise-Muscle图的社区划分
使用networkx的Louvain算法进行社区检测
"""

import json
import os
from collections import defaultdict
from typing import Dict, List, Tuple

import networkx as nx
from neo4j import GraphDatabase


class CommunityDetector:
    """社区检测器"""
    
    def __init__(self, uri="bolt://fitness_neo4j:7687", user="neo4j", password="build_body_2024"):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.graph = nx.Graph()
        self.communities = {}
        
    def close(self):
        self.driver.close()
        
    def fetch_graph_data(self):
        """从Neo4j导出Exercise-Muscle图"""
        print("正在从Neo4j导出图数据...")
        
        query = """
        MATCH (e:Exercise)-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->(m:Muscle)
        RETURN 
            e.name_zh as exercise,
            e.force_zh as force,
            e.mechanic_zh as mechanic,
            e.difficulty_zh as difficulty,
            e.equipment_zh as equipment,
            type(r) as rel_type,
            m.name_zh as muscle
        """
        
        edges = []
        exercise_attrs = {}
        muscle_set = set()
        
        with self.driver.session() as session:
            result = session.run(query)
            for record in result:
                exercise = record["exercise"]
                muscle = record["muscle"]
                rel_type = record["rel_type"]
                
                # 记录边（PRIMARY权重2，SECONDARY权重1）
                weight = 2 if rel_type == "TARGETS_PRIMARY" else 1
                edges.append((exercise, muscle, weight))
                
                # 记录Exercise属性
                if exercise not in exercise_attrs:
                    exercise_attrs[exercise] = {
                        "force": record["force"],
                        "mechanic": record["mechanic"],
                        "difficulty": record["difficulty"],
                        "equipment": record["equipment"],
                        "type": "Exercise"
                    }
                
                # 记录Muscle
                muscle_set.add(muscle)
        
        print(f"导出完成: {len(exercise_attrs)} 个Exercise, {len(muscle_set)} 个Muscle, {len(edges)} 条边")
        
        # 构建networkx图
        for ex, mu, weight in edges:
            self.graph.add_edge(ex, mu, weight=weight)
        
        # 添加节点属性
        for node in self.graph.nodes():
            if node in exercise_attrs:
                nx.set_node_attributes(self.graph, {node: exercise_attrs[node]})
            elif node in muscle_set:
                nx.set_node_attributes(self.graph, {node: {"type": "Muscle"}})
        
        return exercise_attrs, muscle_set
        
    def detect_communities(self):
        """运行Louvain社区检测"""
        print("正在运行Louvain社区检测...")
        
        # networkx的louvain算法
        from networkx.algorithms import community
        communities_generator = community.louvain_communities(self.graph, seed=42)
        
        # 转换为字典格式
        for comm_id, nodes in enumerate(communities_generator):
            for node in nodes:
                self.communities[node] = comm_id
        
        print(f"检测到 {len(set(self.communities.values()))} 个社区")
        return self.communities
        
    def generate_summaries(self, exercise_attrs: Dict, muscle_set: set) -> List[Dict]:
        """生成社区摘要"""
        print("正在生成社区摘要...")
        
        # 按社区分组
        comm_groups = defaultdict(lambda: {"exercises": [], "muscles": []})
        for node, comm_id in self.communities.items():
            if node in exercise_attrs:
                comm_groups[comm_id]["exercises"].append(node)
            elif node in muscle_set:
                comm_groups[comm_id]["muscles"].append(node)
        
        summaries = []
        for comm_id, group in sorted(comm_groups.items()):
            exercises = group["exercises"]
            muscles = group["muscles"]
            
            if not exercises:
                continue
            
            # 统计属性
            force_counts = defaultdict(int)
            mechanic_counts = defaultdict(int)
            difficulty_counts = defaultdict(int)
            equipment_counts = defaultdict(int)
            
            for ex in exercises:
                attrs = exercise_attrs[ex]
                if attrs["force"]:
                    force_counts[attrs["force"]] += 1
                if attrs["mechanic"]:
                    mechanic_counts[attrs["mechanic"]] += 1
                if attrs["difficulty"]:
                    difficulty_counts[attrs["difficulty"]] += 1
                if attrs["equipment"]:
                    eq = attrs["equipment"]
                    if isinstance(eq, list):
                        for e in eq:
                            if e:
                                equipment_counts[e] += 1
                    elif eq:
                        equipment_counts[eq] += 1
            
            # 确定社区名称
            dominant_force = max(force_counts.items(), key=lambda x: x[1])[0] if force_counts else "混合"
            dominant_mechanic = max(mechanic_counts.items(), key=lambda x: x[1])[0] if mechanic_counts else "综合"
            
            force_map = {"push": "推", "pull": "拉", "static": "静态"}
            mechanic_map = {"compound": "复合", "isolation": "孤立"}
            
            comm_name = f"{force_map.get(dominant_force, dominant_force)}-{mechanic_map.get(dominant_mechanic, dominant_mechanic)}动作群"
            
            # 生成摘要
            summary = {
                "community_id": comm_id,
                "name": comm_name,
                "exercise_count": len(exercises),
                "muscle_count": len(muscles),
                "primary_muscles": muscles[:5],  # 前5个肌肉
                "force_distribution": dict(force_counts),
                "mechanic_distribution": dict(mechanic_counts),
                "difficulty_distribution": dict(difficulty_counts),
                "common_equipment": [eq for eq, cnt in sorted(equipment_counts.items(), key=lambda x: -x[1])[:3]],
                "sample_exercises": exercises[:5],  # 示例动作
                "summary": f"包含{len(exercises)}个动作和{len(muscles)}个肌肉的训练群，主要特征为{dominant_force}类{dominant_mechanic}动作"
            }
            
            summaries.append(summary)
            print(f"  社区 {comm_id}: {comm_name} ({len(exercises)} 动作, {len(muscles)} 肌肉)")
        
        return summaries
        
    def write_to_neo4j(self):
        """将社区ID写回Neo4j"""
        print("正在将社区ID写回Neo4j...")
        
        with self.driver.session() as session:
            # 更新Exercise节点
            for node, comm_id in self.communities.items():
                session.run(
                    "MATCH (n) WHERE n.name_zh = $name SET n.community_id = $comm_id",
                    name=node, comm_id=comm_id
                )
        
        print("写入完成")
        
    def save_summaries(self, summaries: List[Dict], output_path: str):
        """保存社区摘要到JSON"""
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summaries, f, ensure_ascii=False, indent=2)
        print(f"社区摘要已保存到: {output_path}")


def main():
    detector = CommunityDetector()
    
    try:
        # 1. 导出图数据
        exercise_attrs, muscle_set = detector.fetch_graph_data()
        
        # 2. 社区检测
        detector.detect_communities()
        
        # 3. 生成摘要
        summaries = detector.generate_summaries(exercise_attrs, muscle_set)
        
        # 4. 写回Neo4j
        detector.write_to_neo4j()
        
        # 5. 保存摘要
        output_path = "/app/data/community_summaries.json"
        detector.save_summaries(summaries, output_path)
        
        # 6. 输出统计
        print("\n=== 社区检测完成 ===")
        print(f"总社区数: {len(summaries)}")
        print(f"总动作数: {len(exercise_attrs)}")
        print(f"总肌肉数: {len(muscle_set)}")
        
    finally:
        detector.close()


if __name__ == "__main__":
    main()
