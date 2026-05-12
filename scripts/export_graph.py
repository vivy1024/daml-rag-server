"""
从 Neo4j 导出图谱数据为 JSON 文件

用法：
  docker exec fitness_daml_rag python -m scripts.export_graph

输出：
  data/graph/exercise_graph.json      — 邻接表（节点→关系→目标节点）
  data/graph/exercise_metadata.json   — Exercise 节点完整属性
  data/graph/food_metadata.json       — Food 节点属性
  data/graph/strength_standards.json  — 力量标准数据
  data/graph/auxiliary_nodes.json     — Muscle/Equipment/InjuryType 等辅助节点
"""

import json
import os
import sys
import time
from datetime import datetime, date


class Neo4jEncoder(json.JSONEncoder):
    """处理 Neo4j 返回的特殊类型"""
    def default(self, obj):
        # neo4j.time.DateTime / Date / Duration 等
        if hasattr(obj, 'iso_format'):
            return obj.iso_format()
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if hasattr(obj, '__float__'):
            return float(obj)
        if hasattr(obj, '__int__'):
            return int(obj)
        return super().default(obj)

# Neo4j 连接配置（容器内）
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "fitness_neo4j_2024")
OUTPUT_DIR = os.getenv("EXPORT_OUTPUT_DIR", "/app/data/graph")


def run_query(driver, query: str, params: dict = None) -> list:
    """执行 Cypher 查询并返回结果列表"""
    with driver.session() as session:
        result = session.run(query, params or {})
        return [dict(record) for record in result]


def export_exercise_metadata(driver) -> dict:
    """导出所有 Exercise 节点的完整属性"""
    print("\n--- 导出 Exercise 节点属性 ---")

    query = """
    MATCH (e:Exercise)
    RETURN e {.*} as props
    """
    results = run_query(driver, query)

    metadata = {}
    for record in results:
        props = record["props"]
        # 用 id 或 name 作为 key
        exercise_id = props.get("id") or props.get("name_en") or props.get("name")
        if exercise_id:
            metadata[str(exercise_id)] = props

    print(f"  导出 {len(metadata)} 个 Exercise 节点")
    return metadata


def export_exercise_graph(driver) -> dict:
    """导出完整的图谱邻接表"""
    print("\n--- 导出图谱关系（邻接表） ---")

    # 获取所有关系类型
    rel_types_query = "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
    rel_types = [r["relationshipType"] for r in run_query(driver, rel_types_query)]
    print(f"  关系类型: {rel_types}")

    # 导出所有关系
    query = """
    MATCH (a)-[r]->(b)
    RETURN
        labels(a)[0] as source_label,
        COALESCE(a.id, a.name_en, a.name) as source_id,
        a.name_zh as source_name_zh,
        a.name as source_name,
        type(r) as rel_type,
        properties(r) as rel_props,
        labels(b)[0] as target_label,
        COALESCE(b.id, b.name_en, b.name) as target_id,
        b.name_zh as target_name_zh,
        b.name as target_name
    """
    results = run_query(driver, query)
    print(f"  总关系数: {len(results)}")

    # 构建邻接表
    graph = {}  # {source_id: {rel_type: [{target_id, target_name, ...}]}}

    for record in results:
        source_id = str(record["source_id"]) if record["source_id"] else None
        target_id = str(record["target_id"]) if record["target_id"] else None
        rel_type = record["rel_type"]

        if not source_id or not target_id:
            continue

        if source_id not in graph:
            graph[source_id] = {
                "_label": record["source_label"],
                "_name_zh": record.get("source_name_zh"),
                "_name": record.get("source_name"),
            }

        if rel_type not in graph[source_id]:
            graph[source_id][rel_type] = []

        edge = {
            "target": target_id,
            "target_label": record["target_label"],
            "target_name_zh": record.get("target_name_zh"),
            "target_name": record.get("target_name"),
        }

        # 添加关系属性
        rel_props = record.get("rel_props")
        if rel_props:
            edge["props"] = rel_props

        graph[source_id][rel_type].append(edge)

    print(f"  邻接表节点数: {len(graph)}")
    return graph


def export_food_metadata(driver) -> dict:
    """导出 Food 节点属性"""
    print("\n--- 导出 Food 节点属性 ---")

    query = """
    MATCH (f:Food)
    RETURN f {.*} as props
    """
    results = run_query(driver, query)

    metadata = {}
    for record in results:
        props = record["props"]
        food_id = props.get("id") or props.get("name_en") or props.get("name")
        if food_id:
            metadata[str(food_id)] = props

    print(f"  导出 {len(metadata)} 个 Food 节点")
    return metadata


def export_strength_standards(driver) -> list:
    """导出力量标准数据"""
    print("\n--- 导出 StrengthStandard 节点 ---")

    query = """
    MATCH (s:StrengthStandard)
    RETURN s {.*} as props
    """
    results = run_query(driver, query)

    standards = [record["props"] for record in results]
    print(f"  导出 {len(standards)} 条力量标准")
    return standards


def export_auxiliary_nodes(driver) -> dict:
    """导出辅助节点（Muscle, Equipment, InjuryType 等）"""
    print("\n--- 导出辅助节点 ---")

    auxiliary_labels = [
        "Muscle", "Equipment", "InjuryType", "PosturalIssue",
        "Joint", "TrainingGoal", "TrainingLevel", "TrainingPhase",
        "PeriodizationModel", "GripType", "ForceType", "KineticChain",
        "MechanicType", "NutrientCategory", "Nutrient",
    ]

    aux_data = {}
    for label in auxiliary_labels:
        query = f"MATCH (n:{label}) RETURN n {{.*}} as props"
        try:
            results = run_query(driver, query)
            nodes = [record["props"] for record in results]
            if nodes:
                aux_data[label] = nodes
                print(f"  {label}: {len(nodes)} 个节点")
        except Exception as e:
            print(f"  {label}: 查询失败 ({e})")

    return aux_data


def main():
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("错误: 需要 neo4j 包")
        print("  pip install neo4j")
        sys.exit(1)

    # 创建输出目录
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 连接 Neo4j
    print(f"连接 Neo4j: {NEO4J_URI}")
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    # 验证连接
    with driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n) as cnt")
        total = result.single()["cnt"]
        print(f"总节点数: {total}")

    start_time = time.time()

    # 1. 导出 Exercise 元数据
    exercise_metadata = export_exercise_metadata(driver)
    with open(os.path.join(OUTPUT_DIR, "exercise_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(exercise_metadata, f, ensure_ascii=False, indent=None, cls=Neo4jEncoder)

    # 2. 导出图谱邻接表
    exercise_graph = export_exercise_graph(driver)
    with open(os.path.join(OUTPUT_DIR, "exercise_graph.json"), "w", encoding="utf-8") as f:
        json.dump(exercise_graph, f, ensure_ascii=False, indent=None, cls=Neo4jEncoder)

    # 3. 导出 Food 元数据
    food_metadata = export_food_metadata(driver)
    with open(os.path.join(OUTPUT_DIR, "food_metadata.json"), "w", encoding="utf-8") as f:
        json.dump(food_metadata, f, ensure_ascii=False, indent=None, cls=Neo4jEncoder)

    # 4. 导出力量标准
    strength_standards = export_strength_standards(driver)
    with open(os.path.join(OUTPUT_DIR, "strength_standards.json"), "w", encoding="utf-8") as f:
        json.dump(strength_standards, f, ensure_ascii=False, indent=None, cls=Neo4jEncoder)

    # 5. 导出辅助节点
    auxiliary_nodes = export_auxiliary_nodes(driver)
    with open(os.path.join(OUTPUT_DIR, "auxiliary_nodes.json"), "w", encoding="utf-8") as f:
        json.dump(auxiliary_nodes, f, ensure_ascii=False, indent=None, cls=Neo4jEncoder)

    # 关闭连接
    driver.close()

    # 汇总
    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"图谱导出完成！耗时: {elapsed:.1f}s")
    print(f"{'='*60}")

    # 文件大小统计
    for fname in os.listdir(OUTPUT_DIR):
        fpath = os.path.join(OUTPUT_DIR, fname)
        size_kb = os.path.getsize(fpath) / 1024
        print(f"  {fname}: {size_kb:.1f} KB")

    # 保存导出元数据
    meta = {
        "export_time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "neo4j_uri": NEO4J_URI,
        "exercise_count": len(exercise_metadata),
        "food_count": len(food_metadata),
        "strength_standards_count": len(strength_standards),
        "graph_nodes": len(exercise_graph),
        "auxiliary_labels": list(auxiliary_nodes.keys()),
    }
    with open(os.path.join(OUTPUT_DIR, "_export_meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2, cls=Neo4jEncoder)


if __name__ == "__main__":
    main()
