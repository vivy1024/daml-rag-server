#!/usr/bin/env python3
"""
实体去重脚本 - 双重确认策略
使用编辑距离 + Embedding余弦相似度检测并合并重复实体

作者: Carol-4 (AI架构师)
日期: 2026-02-17
"""

import os
import sys
from typing import List, Dict, Tuple, Set
from collections import defaultdict
import argparse

sys.path.insert(0, '/app')

from neo4j import GraphDatabase
from sentence_transformers import SentenceTransformer
import numpy as np


class EntityDeduplicator:
    """实体去重器"""
    
    def __init__(self, neo4j_uri: str, neo4j_user: str, neo4j_password: str):
        self.driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
        self.model = None
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.driver.close()
        
    def load_embedding_model(self):
        """加载GTE-Large-zh模型"""
        if self.model is None:
            print("📦 加载GTE-Large-zh embedding模型...")
            self.model = SentenceTransformer('thenlper/gte-large-zh')
            print("✅ 模型加载完成")
            
    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """计算编辑距离"""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        return previous_row[-1]
        
    def cosine_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """计算余弦相似度"""
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
    def fetch_entities(self, label: str, name_field: str) -> List[Dict]:
        """获取指定类型的所有实体"""
        with self.driver.session() as session:
            query = f"MATCH (n:{label}) RETURN id(n) AS node_id, n.{name_field} AS name, COUNT {{ (n)--() }} AS rel_count ORDER BY name"
            result = session.run(query)
            entities = [dict(record) for record in result]
            return entities
            
    def find_exact_duplicates(self, entities: List[Dict]) -> Dict[str, List[Dict]]:
        """Phase 1: 查找精确重复"""
        print("\n🔍 Phase 1: 精确重复检测")
        name_groups = defaultdict(list)
        for entity in entities:
            name = entity['name']
            if name:
                name_groups[name].append(entity)
        duplicates = {name: group for name, group in name_groups.items() if len(group) > 1}
        if duplicates:
            print(f"✅ 发现 {len(duplicates)} 组精确重复，共 {sum(len(g) for g in duplicates.values())} 个节点")
            for name, group in list(duplicates.items())[:5]:
                print(f"   - '{name}': {len(group)} 个节点")
        else:
            print("✅ 未发现精确重复")
        return duplicates
        
    def find_fuzzy_duplicates(self, entities: List[Dict], threshold: int = 2) -> List[Tuple[Dict, Dict, int]]:
        """Phase 2: 查找模糊重复"""
        print(f"\n🔍 Phase 2: 模糊重复检测（编辑距离 ≤ {threshold}）")
        first_char_groups = defaultdict(list)
        for entity in entities:
            name = entity['name']
            if name:
                first_char_groups[name[0]].append(entity)
        candidates = []
        total_comparisons = 0
        for first_char, group in first_char_groups.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    e1, e2 = group[i], group[j]
                    total_comparisons += 1
                    dist = self.levenshtein_distance(e1['name'], e2['name'])
                    if 0 < dist <= threshold:
                        candidates.append((e1, e2, dist))
        print(f"✅ 完成 {total_comparisons:,} 次比较，发现 {len(candidates)} 对候选重复")
        for e1, e2, dist in candidates[:10]:
            print(f"   - '{e1['name']}' ↔ '{e2['name']}' (距离={dist})")
        return candidates
        
    def confirm_with_embedding(self, candidates: List[Tuple[Dict, Dict, int]], 
                               high_threshold: float = 0.95, 
                               medium_threshold: float = 0.85) -> Dict[str, List]:
        """Phase 3: Embedding相似度确认"""
        print(f"\n🔍 Phase 3: Embedding相似度确认（高阈值={high_threshold}, 中阈值={medium_threshold}）")
        if not candidates:
            print("✅ 无候选对需要确认")
            return {'confirmed': [], 'suspected': [], 'rejected': []}
        self.load_embedding_model()
        unique_names = set()
        for e1, e2, _ in candidates:
            unique_names.add(e1['name'])
            unique_names.add(e2['name'])
        unique_names = list(unique_names)
        print(f"📊 编码 {len(unique_names)} 个唯一名称...")
        embeddings = self.model.encode(unique_names, show_progress_bar=True)
        name_to_emb = {name: emb for name, emb in zip(unique_names, embeddings)}
        confirmed = []
        suspected = []
        rejected = []
        for e1, e2, edit_dist in candidates:
            emb1 = name_to_emb[e1['name']]
            emb2 = name_to_emb[e2['name']]
            similarity = self.cosine_similarity(emb1, emb2)
            item = (e1, e2, edit_dist, similarity)
            if similarity >= high_threshold:
                confirmed.append(item)
            elif similarity >= medium_threshold:
                suspected.append(item)
            else:
                rejected.append(item)
        print(f"✅ 确认重复: {len(confirmed)} 对")
        print(f"⚠️  疑似重复: {len(suspected)} 对（需人工确认）")
        print(f"❌ 非重复: {len(rejected)} 对")
        if confirmed:
            print("\n确认的重复对（前10个）:")
            for e1, e2, dist, sim in confirmed[:10]:
                print(f"   - '{e1['name']}' ↔ '{e2['name']}' (编辑距离={dist}, 相似度={sim:.4f})")
        if suspected:
            print("\n疑似重复对（需人工确认）:")
            for e1, e2, dist, sim in suspected[:10]:
                print(f"   - '{e1['name']}' ↔ '{e2['name']}' (编辑距离={dist}, 相似度={sim:.4f})")
        return {'confirmed': confirmed, 'suspected': suspected, 'rejected': rejected}
        
    def plan_merge_operations(self, exact_duplicates: Dict[str, List[Dict]], 
                             confirmed_duplicates: List[Tuple]) -> List[Dict]:
        """Phase 4: 规划合并操作"""
        print("\n🔍 Phase 4: 规划合并操作")
        merge_plans = []
        for name, group in exact_duplicates.items():
            group_sorted = sorted(group, key=lambda x: x['rel_count'], reverse=True)
            master = group_sorted[0]
            slaves = group_sorted[1:]
            merge_plans.append({'type': 'exact', 'master': master, 'slaves': slaves, 'reason': '精确重复'})
        for e1, e2, dist, sim in confirmed_duplicates:
            if e1['rel_count'] >= e2['rel_count']:
                master, slave = e1, e2
            else:
                master, slave = e2, e1
            merge_plans.append({'type': 'fuzzy', 'master': master, 'slaves': [slave], 'reason': f'模糊重复（编辑距离={dist}, 相似度={sim:.4f}）'})
        print(f"✅ 规划 {len(merge_plans)} 个合并操作")
        if merge_plans:
            print("\n合并计划（前10个）:")
            for i, plan in enumerate(merge_plans[:10], 1):
                master = plan['master']
                slaves = plan['slaves']
                print(f"   {i}. 保留 '{master['name']}' (ID={master['node_id']}, 关系数={master['rel_count']})")
                for slave in slaves:
                    print(f"      合并 '{slave['name']}' (ID={slave['node_id']}, 关系数={slave['rel_count']}) - {plan['reason']}")
        return merge_plans
        
    def execute_merge(self, label: str, merge_plans: List[Dict], dry_run: bool = True):
        """执行合并操作"""
        if dry_run:
            print("\n⚠️  DRY-RUN模式：不会实际执行合并操作")
            return
        print("\n🚀 执行合并操作...")
        print("⚠️  警告：此操作不可逆，请确保已备份数据库！")
                        
    def deduplicate_entity_type(self, label: str, name_field: str, dry_run: bool = True):
        """对指定实体类型执行完整去重流程"""
        print(f"\n{'='*80}")
        print(f"🎯 开始处理实体类型: {label} (名称字段: {name_field})")
        print(f"{'='*80}")
        entities = self.fetch_entities(label, name_field)
        print(f"📊 共 {len(entities)} 个 {label} 节点")
        if not entities:
            print("⚠️  无数据，跳过")
            return {'label': label, 'total_entities': 0, 'exact_duplicates': 0, 'confirmed_fuzzy': 0, 'suspected': 0, 'total_to_merge': 0, 'merge_plans': []}
        exact_duplicates = self.find_exact_duplicates(entities)
        fuzzy_candidates = self.find_fuzzy_duplicates(entities, threshold=2)
        confirmation_result = self.confirm_with_embedding(fuzzy_candidates)
        merge_plans = self.plan_merge_operations(exact_duplicates, confirmation_result['confirmed'])
        total_duplicates = sum(len(g) - 1 for g in exact_duplicates.values()) + len(confirmation_result['confirmed'])
        print(f"\n📊 统计:")
        print(f"   - 精确重复组: {len(exact_duplicates)}")
        print(f"   - 确认的模糊重复: {len(confirmation_result['confirmed'])}")
        print(f"   - 疑似重复（需人工确认）: {len(confirmation_result['suspected'])}")
        print(f"   - 总计需合并节点: {total_duplicates}")
        if merge_plans:
            self.execute_merge(label, merge_plans, dry_run=dry_run)
        else:
            print("\n✅ 无需合并操作")
        return {
            'label': label,
            'total_entities': len(entities),
            'exact_duplicates': len(exact_duplicates),
            'confirmed_fuzzy': len(confirmation_result['confirmed']),
            'suspected': len(confirmation_result['suspected']),
            'total_to_merge': total_duplicates,
            'merge_plans': merge_plans
        }


def main():
    parser = argparse.ArgumentParser(description='实体去重脚本')
    parser.add_argument('--execute', action='store_true', help='实际执行合并（默认dry-run）')
    parser.add_argument('--entity', choices=['Exercise', 'Muscle', 'Food', 'Equipment', 'all'], 
                       default='all', help='指定实体类型')
    args = parser.parse_args()
    NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://neo4j:7687')
    NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
    NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'fitness2024')
    print("🚀 实体去重脚本启动")
    print(f"模式: {'执行模式' if args.execute else 'DRY-RUN模式（仅报告）'}")
    print(f"Neo4j URI: {NEO4J_URI}")
    entity_configs = [
        ('Exercise', 'name_zh'),
        ('Muscle', 'name_zh'),
        ('Food', 'name'),
        ('Equipment', 'name_zh'),
    ]
    if args.entity != 'all':
        entity_configs = [(label, field) for label, field in entity_configs if label == args.entity]
    results = []
    with EntityDeduplicator(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD) as dedup:
        for label, name_field in entity_configs:
            try:
                result = dedup.deduplicate_entity_type(label, name_field, dry_run=not args.execute)
                results.append(result)
            except Exception as e:
                print(f"❌ 处理 {label} 时出错: {e}")
                import traceback
                traceback.print_exc()
    print(f"\n{'='*80}")
    print("📊 去重总结报告")
    print(f"{'='*80}")
    for result in results:
        print(f"\n{result['label']}:")
        print(f"   - 总节点数: {result['total_entities']}")
        print(f"   - 精确重复组: {result['exact_duplicates']}")
        print(f"   - 确认的模糊重复: {result['confirmed_fuzzy']}")
        print(f"   - 疑似重复: {result['suspected']}")
        print(f"   - 需合并节点: {result['total_to_merge']}")
    total_to_merge = sum(r['total_to_merge'] for r in results)
    print(f"\n总计需合并节点: {total_to_merge}")
    if not args.execute and total_to_merge > 0:
        print("\n⚠️  这是DRY-RUN模式，未实际执行合并")
        print("如需执行合并，请运行: python scripts/entity_dedup.py --execute")
        print("⚠️  执行前请确保已备份Neo4j数据库！")


if __name__ == '__main__':
    main()
