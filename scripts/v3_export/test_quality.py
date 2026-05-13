"""调试搜索质量"""
import os, asyncio, json
os.environ["DATA_DIR"] = "/app/data/v3"

from src_v2.config import get_config
from src_v2.data.loader import DataStore
from src_v2.engine.wave_engine import WaveEngine
from src_v2.tools.embedding import encode_query, warmup

cfg = get_config()
data = DataStore(config=cfg.data)
asyncio.run(data.load())
engine = WaveEngine(data_store=data, config=cfg.engine)
warmup()

# 直接向量搜索（不经过引擎管线）
query_vec = encode_query("练胸的动作")
raw_results = data.exercise_index.search(query_vec, k=10)

print("=== 原始向量搜索: 练胸的动作 ===")
for idx, sim in raw_results:
    payload = data.exercise_payloads[idx]
    name = payload.get("name_zh", "")
    muscles = payload.get("muscles_primary_zh", [])
    print(f"  [{sim:.4f}] {name} | 主肌群: {muscles}")

# 对比引擎管线
print("\n=== WaveEngine 管线 ===")
result = asyncio.run(engine.search(query_vec=query_vec, domain="exercises", top_k=10))
for item in result.results[:10]:
    name = item.get("name_zh", "")
    score = item["score"]
    print(f"  [{score:.4f}] {name}")

# 知识搜索调试
print("\n=== 知识搜索: 渐进超负荷 ===")
query_vec2 = encode_query("渐进超负荷原则")
raw_k = data.knowledge_index.search(query_vec2, k=5)
for idx, sim in raw_k:
    payload = data.knowledge_payloads[idx]
    print(f"  [{sim:.4f}] keys={list(payload.keys())[:8]}")
    if "title" in payload:
        print(f"           title={payload['title'][:50]}")
    elif "chunk_title" in payload:
        print(f"           chunk_title={payload['chunk_title'][:50]}")
    elif "text" in payload:
        print(f"           text={payload['text'][:50]}")

# 食物搜索调试
print("\n=== 食物搜索: 高蛋白 ===")
query_vec3 = encode_query("高蛋白食物")
raw_f = data.food_index.search(query_vec3, k=5)
for idx, sim in raw_f:
    payload = data.food_payloads[idx]
    print(f"  [{sim:.4f}] keys={list(payload.keys())[:8]}")
    name = payload.get("name", payload.get("food_name", ""))
    print(f"           name={name}")
