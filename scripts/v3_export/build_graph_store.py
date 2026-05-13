"""
Phase 0 Task 0.2b: 将导出的原始图谱数据转换为 GraphStore 期望的格式

GraphStore 期望格式:
{
  "node_id": {
    "_label": "Exercise",
    "_name_zh": "卧推",
    "TARGETS_PRIMARY": [{"target": "muscle_id", "target_label": "Muscle", "target_name_zh": "胸大肌"}],
    ...
  }
}
"""

import json
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent.parent / "data" / "v3"


def build_graph_store_format():
    """将原始邻接表 + 元数据转换为 GraphStore 格式"""

    # 加载原始邻接表
    with open(DATA_DIR / "exercise_graph.json", "r", encoding="utf-8") as f:
        raw_adjacency = json.load(f)

    # 加载元数据
    with open(DATA_DIR / "exercise_metadata.json", "r", encoding="utf-8") as f:
        exercise_meta = json.load(f)

    with open(DATA_DIR / "food_metadata.json", "r", encoding="utf-8") as f:
        food_meta = json.load(f)

    with open(DATA_DIR / "auxiliary_nodes.json", "r", encoding="utf-8") as f:
        auxiliary = json.load(f)

    with open(DATA_DIR / "strength_standards.json", "r", encoding="utf-8") as f:
        strength_meta = json.load(f)

    # 构建 node_id → (label, name_zh) 映射
    id_to_info = {}

    for nid, props in exercise_meta.items():
        id_to_info[nid] = ("Exercise", props.get("name_zh", props.get("name", "")))

    for nid, props in food_meta.items():
        id_to_info[nid] = ("Food", props.get("name", ""))

    for nid, props in strength_meta.items():
        id_to_info[nid] = ("StrengthStandard", props.get("exercise_name", ""))

    for label, nodes in auxiliary.items():
        for nid, props in nodes.items():
            name = props.get("name_zh", props.get("name", props.get("display_name", "")))
            id_to_info[nid] = (label, name)

    print(f"节点信息映射: {len(id_to_info)} 个节点")

    # 构建 GraphStore 格式
    graph = {}

    for source_id, edges in raw_adjacency.items():
        if source_id not in graph:
            src_label, src_name = id_to_info.get(source_id, ("Unknown", ""))
            graph[source_id] = {
                "_label": src_label,
                "_name_zh": src_name,
            }

        for edge in edges:
            target_id = edge["target"]
            rel_type = edge["type"]
            props = edge.get("props", {})

            tgt_label, tgt_name = id_to_info.get(target_id, ("Unknown", ""))

            if rel_type not in graph[source_id]:
                graph[source_id][rel_type] = []

            graph[source_id][rel_type].append({
                "target": target_id,
                "target_label": tgt_label,
                "target_name_zh": tgt_name,
                "props": props,
            })

    # 确保所有节点都在图中（即使没有出边）
    for nid, (label, name) in id_to_info.items():
        if nid not in graph:
            graph[nid] = {
                "_label": label,
                "_name_zh": name,
            }

    # 保存
    output_path = DATA_DIR / "graph" / "exercise_graph.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, ensure_ascii=False)

    print(f"GraphStore 格式输出: {output_path}")
    print(f"  节点数: {len(graph)}")

    # 统计关系
    rel_count = 0
    rel_types = {}
    for node_data in graph.values():
        for key, val in node_data.items():
            if key.startswith("_") or not isinstance(val, list):
                continue
            rel_count += len(val)
            rel_types[key] = rel_types.get(key, 0) + len(val)

    print(f"  关系数: {rel_count}")
    print(f"  关系类型:")
    for rt, cnt in sorted(rel_types.items(), key=lambda x: -x[1]):
        print(f"    {rt}: {cnt}")


if __name__ == "__main__":
    build_graph_store_format()
