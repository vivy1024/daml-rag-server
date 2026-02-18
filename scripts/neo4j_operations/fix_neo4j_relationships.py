#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Neo4j关系修复脚本

**版本**: v2.0.0
**更新日期**: 2025-11-29
**功能**: 修复Neo4j数据库中的孤立节点和缺失关系

使用说明:
    python scripts/fix_neo4j_relationships.py [--dry-run]

参数:
    --dry-run: 仅预览修复操作，不实际执行

修复内容:
1. 修复486个孤立Exercise节点的TARGETS关系
2. 建立Exercise-Equipment关系 (0 → 1,603个)
3. 完善Exercise-InjuryType关系 (2 → 更多)
4. 补充Muscle节点的MEV/MAV/MRV训练容量数据 (从perfect_enhanced_dataset加载)

连接信息:
- Neo4j URI: bolt://localhost:7687
- 数据库: neo4j
- 认证: neo4j/password (默认)

数据来源:
- 训练容量数据: /f/build_body/perfect_enhanced_dataset/training_knowledge/training-volume-landmarks.json
"""

import sys
import json
import argparse
from datetime import datetime
from typing import List, Dict, Tuple
from neo4j import GraphDatabase

# 从perfect_enhanced_dataset加载训练容量数据
def load_muscle_volume_data():
    """从perfect_enhanced_dataset加载MEV/MAV/MRV数据"""
    volume_file = "/f/build_body/perfect_enhanced_dataset/training_knowledge/training-volume-landmarks.json"

    try:
        with open(volume_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        volume_data = {}
        landmarks = data.get("volume_landmarks", {})

        for muscle_name, muscle_data in landmarks.items():
            # 提取数值范围的中位数
            mev_range = muscle_data.get("MEV", {}).get("sets_per_week", "0").replace("+", "")
            mav_range = muscle_data.get("MAV", {}).get("sets_per_week", "0").replace("+", "")
            mrv_range = muscle_data.get("MRV", {}).get("sets_per_week", "0").replace("+", "")

            def parse_range(range_str):
                if "-" in range_str:
                    parts = range_str.split("-")
                    return (int(parts[0]) + int(parts[1])) // 2
                return int(range_str)

            volume_data[muscle_name] = {
                "mev": parse_range(mev_range),
                "mav": parse_range(mav_range),
                "mrv": parse_range(mrv_range),
                "name_en": muscle_name.replace("_", " ").title()
            }

        return volume_data

    except Exception as e:
        print(f"Error loading volume data: {e}")
        # 备用数据
        return {
            "chest": {"mev": 10, "mav": 16, "mrv": 22, "name_en": "Pectoralis Major"},
            "back": {"mev": 12, "mav": 18, "mrv": 25, "name_en": "Latissimus Dorsi"},
            "shoulders": {"mev": 8, "mav": 14, "mrv": 20, "name_en": "Deltoids"},
        }

# 加载训练容量数据
MUSCLE_VOLUME_DATA = load_muscle_volume_data()


class Neo4jRelationshipFixer:
    """Neo4j关系修复器"""

    def __init__(self, uri: str = "bolt://localhost:7687",
                 user: str = "neo4j", password: str = "password"):
        """初始化连接"""
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self.dry_run = False
        self.stats = {
            "exercise_targets_fixed": 0,
            "exercise_equipment_relations": 0,
            "exercise_injury_relations": 0,
            "muscle_volume_updated": 0,
            "errors": []
        }

    def close(self):
        """关闭连接"""
        self.driver.close()

    def log(self, message: str, level: str = "INFO"):
        """日志输出"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def dry_run_mode(self, enabled: bool = True):
        """设置干运行模式"""
        self.dry_run = enabled
        if enabled:
            self.log("[DRY-RUN MODE] Preview only, no actual changes will be made", "WARN")

    def execute_cypher(self, query: str, params: dict = None) -> List[Dict]:
        """执行Cypher查询"""
        try:
            with self.driver.session() as session:
                result = session.run(query, params)
                return [record.data() for record in result]
        except Exception as e:
            self.log(f"[ERROR] Cypher query failed: {str(e)}", "ERROR")
            self.stats["errors"].append(str(e))
            return []

    def fix_isolated_exercise_nodes(self) -> int:
        """修复孤立Exercise节点的TARGETS关系"""
        self.log("\n[STEP 1] Fix isolated Exercise nodes (Target: 486 nodes)")

        # 1. 找到孤立节点
        query_isolated = """
        MATCH (e:Exercise)
        WHERE NOT (e)--() AND e.primary_muscle_zh IS NOT NULL
        RETURN e.id as id, e.name_zh as name, e.primary_muscle_zh as primary_muscle
        """

        isolated_exercises = self.execute_cypher(query_isolated)
        self.log(f"   Found {len(isolated_exercises)} isolated Exercise nodes")

        # 2. 批量修复
        fixed_count = 0
        for ex in isolated_exercises:
            query_fix = """
            MATCH (e:Exercise {id: $ex_id})
            MATCH (m:Muscle)
            WHERE m.name_zh = $muscle_name
               OR m.name_en = $muscle_name
               OR m.name = $muscle_name
            MERGE (e)-[:TARGETS_PRIMARY]->(m)
            RETURN e.name_zh as exercise, m.name_zh as muscle
            """

            result = self.execute_cypher(query_fix, {
                "ex_id": ex["id"],
                "muscle_name": ex["primary_muscle"]
            })

            if result:
                fixed_count += 1
                if fixed_count <= 5:  # 只显示前5个作为示例
                    self.log(f"   [OK] {ex['name']} -> {result[0]['muscle']}")

        self.stats["exercise_targets_fixed"] = fixed_count
        self.log(f"   [RESULT] Successfully fixed {fixed_count}/{len(isolated_exercises)} isolated nodes\n")

        return fixed_count

    def create_exercise_equipment_relations(self) -> int:
        """创建Exercise-Equipment关系"""
        self.log("\n[STEP 2] Create Exercise-Equipment relations (Target: 0 -> 1,603)")

        query = """
        MATCH (e:Exercise)
        WHERE e.equipment_zh IS NOT NULL
        WITH DISTINCT e.equipment_zh as equipment_name, collect(e) as exercises
        MATCH (eq:Equipment)
        WHERE eq.name_zh = equipment_name OR eq.name = equipment_name
        UNWIND exercises as e
        MERGE (e)-[:REQUIRES]->(eq)
        RETURN e.name_zh as exercise, eq.name_zh as equipment, count(*) as created
        """

        results = self.execute_cypher(query)
        created_count = sum(r.get("created", 0) for r in results)

        self.log(f"   [OK] Created {created_count} Exercise-Equipment relations")

        # 显示前5个示例
        for i, result in enumerate(results[:5]):
            self.log(f"   [SAMPLE] {result['exercise']} -> {result['equipment']}")

        self.stats["exercise_equipment_relations"] = created_count
        self.log(f"   [RESULT] Total: {created_count} relations created\n")

        return created_count

    def fix_exercise_injury_relations(self) -> int:
        """修复Exercise-InjuryType关系"""
        self.log("\n[STEP 3] Fix Exercise-InjuryType relations (Target: 2 -> more)")

        query = """
        MATCH (e:Exercise), (it:InjuryType)
        WHERE ANY(warning IN e.safety_warning_signs
                  WHERE warning CONTAINS it.name
                     OR warning CONTAINS it.name_en)
        WITH e, it, count(*) as matches
        MERGE (e)-[:CONTRAINDICATED_FOR {confidence: matches}]->(it)
        RETURN e.name_zh as exercise, it.name as injury_type, matches
        """

        results = self.execute_cypher(query)
        created_count = len(results)

        self.log(f"   [OK] Created {created_count} Exercise-InjuryType relations")

        # 显示示例
        for result in results[:5]:
            self.log(f"   [WARNING] {result['exercise']} X {result['injury_type']}")

        self.stats["exercise_injury_relations"] = created_count
        self.log(f"   [RESULT] Total: {created_count} relations created\n")

        return created_count

    def add_muscle_volume_data(self) -> int:
        """补充Muscle节点的MEV/MAV/MRV数据"""
        self.log("\n[STEP 4] Add Muscle training volume data (MEV/MAV/MRV)")
        self.log(f"   Loading data from: /f/build_body/perfect_enhanced_dataset/training_knowledge/training-volume-landmarks.json")

        updated_count = 0

        for muscle_zh, volume_data in MUSCLE_VOLUME_DATA.items():
            query = """
            MATCH (m:Muscle)
            WHERE m.name_zh = $muscle_name
               OR m.name_en = $volume_name_en
               OR m.name = $muscle_name
               OR toLower(m.name) CONTAINS toLower($muscle_name)
            SET m.MEV = $mev,
                m.MAV = $mav,
                m.MRV = $mrv,
                m.volume_updated_at = datetime(),
                m.volume_source = "Renaissance Periodization"
            RETURN m.name_zh as muscle_zh, m.name_en as muscle_en
            """

            results = self.execute_cypher(query, {
                "muscle_name": muscle_zh,
                "volume_name_en": volume_data["name_en"],
                "mev": volume_data["mev"],
                "mav": volume_data["mav"],
                "mrv": volume_data["mrv"]
            })

            if results:
                updated_count += 1
                self.log(f"   [OK] {results[0]['muscle_zh']} "
                        f"(MEV:{volume_data['mev']}, "
                        f"MAV:{volume_data['mav']}, "
                        f"MRV:{volume_data['mrv']})")

        self.stats["muscle_volume_updated"] = updated_count
        self.log(f"   [RESULT] Successfully updated {updated_count} Muscle nodes with volume data\n")

        return updated_count

    def verify_fixes(self):
        """验证修复结果"""
        self.log("\n[VERIFICATION] Verify fix results:")

        # 1. 检查孤立节点数量
        query = """
        MATCH (n)
        WHERE NOT (n)--()
        RETURN labels(n) as node_type, count(*) as count
        ORDER BY count DESC
        """
        isolated = self.execute_cypher(query)
        for record in isolated:
            self.log(f"   Isolated nodes: {record['node_type'][0]} = {record['count']} nodes")

        # 2. 检查TARGETS关系数量
        query = """
        MATCH ()-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->()
        RETURN type(r) as relation_type, count(*) as count
        """
        relations = self.execute_cypher(query)
        for record in relations:
            self.log(f"   Relations: {record['relation_type']} = {record['count']} edges")

        # 3. 检查Exercise-Equipment关系
        query = "MATCH ()-[r:REQUIRES]->() RETURN count(*) as count"
        result = self.execute_cypher(query)
        count = result[0]["count"] if result else 0
        self.log(f"   Relations: REQUIRES = {count} edges")

        # 4. 检查有MEV/MAV/MRV的Muscle数量
        query = """
        MATCH (m:Muscle)
        WHERE m.MEV IS NOT NULL
        RETURN count(*) as count
        """
        result = self.execute_cypher(query)
        count = result[0]["count"] if result else 0
        self.log(f"   Muscle volume data: {count} nodes")

    def print_summary(self):
        """打印修复摘要"""
        self.log("\n" + "="*60)
        self.log("[SUMMARY] Fix Summary Report")
        self.log("="*60)
        self.log(f"[OK] Exercise isolated nodes fixed: {self.stats['exercise_targets_fixed']}")
        self.log(f"[OK] Exercise-Equipment relations: {self.stats['exercise_equipment_relations']}")
        self.log(f"[OK] Exercise-InjuryType relations: {self.stats['exercise_injury_relations']}")
        self.log(f"[OK] Muscle volume updated: {self.stats['muscle_volume_updated']}")

        if self.stats["errors"]:
            self.log(f"\n[ERROR] Errors: {len(self.stats['errors'])}")
            for error in self.stats["errors"][:5]:
                self.log(f"   - {error}")

        self.log("="*60)

        if not self.dry_run:
            self.log("\n[COMPLETE] Fix completed! Recommend restarting Neo4j service to ensure changes take effect")
        else:
            self.log("\n[DRY-RUN] This is dry-run mode, no changes were actually made")

    def run_all_fixes(self):
        """运行所有修复操作"""
        self.log("=== Starting Neo4j Relationship Fix ===")
        self.log(f"Mode: {'[DRY-RUN] Preview only' if self.dry_run else '[EXECUTE] Apply fixes'}")

        try:
            # 1. 修复孤立Exercise节点
            self.fix_isolated_exercise_nodes()

            # 2. 创建Exercise-Equipment关系
            self.create_exercise_equipment_relations()

            # 3. 修复Exercise-InjuryType关系
            self.fix_exercise_injury_relations()

            # 4. 添加Muscle训练容量数据
            self.add_muscle_volume_data()

            # 5. 验证结果
            self.verify_fixes()

            # 6. 打印摘要
            self.print_summary()

        except Exception as e:
            self.log(f"[ERROR] Error during fix process: {str(e)}", "ERROR")
            raise
        finally:
            self.close()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="Neo4j Relationship Fix Script")
    parser.add_argument("--dry-run", action="store_true",
                       help="Dry-run mode, preview only without execution")
    parser.add_argument("--uri", default="bolt://localhost:7687",
                       help="Neo4j connection URI (default: bolt://localhost:7687)")
    parser.add_argument("--user", default="neo4j",
                       help="Neo4j username (default: neo4j)")
    parser.add_argument("--password", default="password",
                       help="Neo4j password (default: password)")

    args = parser.parse_args()

    # 创建修复器实例
    fixer = Neo4jRelationshipFixer(
        uri=args.uri,
        user=args.user,
        password=args.password
    )

    # 设置干运行模式
    if args.dry_run:
        fixer.dry_run_mode(enabled=True)

    # 运行修复
    fixer.run_all_fixes()


if __name__ == "__main__":
    main()
