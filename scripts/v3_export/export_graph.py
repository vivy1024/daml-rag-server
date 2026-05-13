"""
Phase 0 Task 0.2: 从 Neo4j 导出图谱数据为 JSON 文件

导出内容:
  - exercise_metadata.json: 1790 个 Exercise 节点全部属性
  - food_metadata.json: 1880 个 Food 节点全部属性
  - exercise_graph.json: 邻接表格式的关系图谱
  - strength_standards.json: 360 个力量标准
  - auxiliary_nodes.json: Muscle/Equipment/InjuryType 等辅助节点

输出到 data/v3/ 目录
"""

import json
import sys
from pathlib import Path

from neo4j import GraphDatabase

# 配置
NEO4J_URI = "bolt://localhost:7687"
NEO4J_USER = "neo4j"
NEO4J_PASSWORD = "build_body_2024"
OUTPUT_DIR = Path(__file__).parent.parent.parent / "data" / "v3"


def neo4j_value_to_json(value):
    """将 Neo4j 值转为 JSON 可序列化类型"""
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, list):
        return [neo4j_value_to_json(v) for v in value]
    if isinstance(value, dict):
        return {k: neo4j_value_to_json(v) for k, v in value.items()}
    return str(value)


def export_exercises(session, output_dir: Path):
    """导出所有 Exercise 节点"""
    print("\n导出 Exercise 节点...")
    result = session.run("""
        MATCH (e:Exercise)
        RETURN e, elementId(e) as eid
        ORDER BY e.name
    """)

    exercises = {}
    for record in result:
        node = record["e"]
        eid = record["eid"]
        props = {k: neo4j_value_to_json(v) for k, v in dict(node).items()}
        exercises[eid] = props

    path = output_dir / "exercise_metadata.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(exercises, f, ensure_ascii=False, indent=2)
    print(f"  {len(exercises)} 个 Exercise 节点 → {path.name}")
    return exercises


def export_foods(session, output_dir: Path):
    """导出所有 Food 节点"""
    print("\n导出 Food 节点...")
    result = session.run("""
        MATCH (f:Food)
        RETURN f, elementId(f) as fid
        ORDER BY f.name
    """)

    foods = {}
    for record in result:
        node = record["f"]
        fid = record["fid"]
        props = {k: neo4j_value_to_json(v) for k, v in dict(node).items()}
        foods[fid] = props

    path = output_dir / "food_metadata.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(foods, f, ensure_ascii=False, indent=2)
    print(f"  {len(foods)} 个 Food 节点 → {path.name}")
    return foods


def export_graph(session, output_dir: Path):
    """导出所有关系为邻接表格式"""
    print("\n导出关系图谱...")
    result = session.run("""
        MATCH (a)-[r]->(b)
        RETURN elementId(a) as src, elementId(b) as dst, 
               type(r) as rel_type, properties(r) as props,
               labels(a)[0] as src_label, labels(b)[0] as dst_label
    """)

    # 邻接表: { node_id: [ {target, rel_type, props}, ... ] }
    adjacency = {}
    rel_count = 0

    for record in result:
        src = record["src"]
        dst = record["dst"]
        rel_type = record["rel_type"]
        props = neo4j_value_to_json(record["props"]) or {}

        if src not in adjacency:
            adjacency[src] = []
        adjacency[src].append({
            "target": dst,
            "type": rel_type,
            "props": props,
        })
        rel_count += 1

    path = output_dir / "exercise_graph.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(adjacency, f, ensure_ascii=False)
    print(f"  {rel_count} 条关系, {len(adjacency)} 个源节点 → {path.name}")

    # 同时导出反向邻接表（用于反向查询）
    reverse_adjacency = {}
    result = session.run("""
        MATCH (a)-[r]->(b)
        RETURN elementId(a) as src, elementId(b) as dst, 
               type(r) as rel_type, properties(r) as props
    """)
    for record in result:
        src = record["src"]
        dst = record["dst"]
        rel_type = record["rel_type"]
        props = neo4j_value_to_json(record["props"]) or {}

        if dst not in reverse_adjacency:
            reverse_adjacency[dst] = []
        reverse_adjacency[dst].append({
            "source": src,
            "type": rel_type,
            "props": props,
        })

    path = output_dir / "exercise_graph_reverse.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(reverse_adjacency, f, ensure_ascii=False)
    print(f"  反向邻接表 → {path.name}")


def export_strength_standards(session, output_dir: Path):
    """导出力量标准"""
    print("\n导出 StrengthStandard 节点...")
    result = session.run("""
        MATCH (s:StrengthStandard)
        RETURN s, elementId(s) as sid
    """)

    standards = {}
    for record in result:
        node = record["s"]
        sid = record["sid"]
        props = {k: neo4j_value_to_json(v) for k, v in dict(node).items()}
        standards[sid] = props

    path = output_dir / "strength_standards.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(standards, f, ensure_ascii=False, indent=2)
    print(f"  {len(standards)} 个 StrengthStandard → {path.name}")


def export_auxiliary_nodes(session, output_dir: Path):
    """导出辅助节点（Muscle, Equipment, InjuryType 等）"""
    print("\n导出辅助节点...")

    auxiliary_labels = [
        "Muscle", "Equipment", "InjuryType", "PosturalIssue",
        "Joint", "TrainingGoal", "TrainingLevel", "TrainingParams",
        "Nutrient", "NutrientCategory", "GripType", "ForceType",
        "MechanicType", "KineticChain", "PeriodizationModel",
        "TrainingPhase", "WorkoutProgram", "RehabilitationPhase",
    ]

    auxiliary = {}
    for label in auxiliary_labels:
        result = session.run(f"""
            MATCH (n:{label})
            RETURN n, elementId(n) as nid
        """)
        nodes = {}
        for record in result:
            node = record["n"]
            nid = record["nid"]
            props = {k: neo4j_value_to_json(v) for k, v in dict(node).items()}
            nodes[nid] = props
        if nodes:
            auxiliary[label] = nodes
            print(f"  {label}: {len(nodes)} 个")

    path = output_dir / "auxiliary_nodes.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(auxiliary, f, ensure_ascii=False, indent=2)
    print(f"  辅助节点 → {path.name}")


def export_node_id_mapping(session, output_dir: Path):
    """导出 elementId → name 的映射表（用于脉冲传播时快速查找）"""
    print("\n导出节点 ID-Name 映射...")
    result = session.run("""
        MATCH (n)
        WHERE n.name IS NOT NULL
        RETURN elementId(n) as nid, n.name as name, labels(n)[0] as label
    """)

    mapping = {}
    name_to_id = {}
    for record in result:
        nid = record["nid"]
        name = record["name"]
        label = record["label"]
        mapping[nid] = {"name": name, "label": label}
        # name → id 反向映射（用于查询时从名字找节点）
        key = f"{label}:{name}"
        name_to_id[key] = nid

    path = output_dir / "node_id_mapping.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False)
    print(f"  {len(mapping)} 个节点映射 → {path.name}")

    path = output_dir / "name_to_id_mapping.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(name_to_id, f, ensure_ascii=False)
    print(f"  反向映射 → {path.name}")


def main():
    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Neo4j 图谱导出工具")
    print(f"连接: {NEO4J_URI}")
    print(f"输出目录: {output_dir}")

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        export_exercises(session, output_dir)
        export_foods(session, output_dir)
        export_graph(session, output_dir)
        export_strength_standards(session, output_dir)
        export_auxiliary_nodes(session, output_dir)
        export_node_id_mapping(session, output_dir)

    driver.close()

    print(f"\n{'='*60}")
    print(f"导出完成！文件列表:")
    for f in sorted(output_dir.glob("*.json")):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"  {f.name} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
