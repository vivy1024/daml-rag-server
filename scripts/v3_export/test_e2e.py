"""容器内端到端测试"""
import os, time, asyncio, json
os.environ["DATA_DIR"] = "/app/data/v3"

from src_v2.config import get_config
from src_v2.data.loader import DataStore
from src_v2.engine.wave_engine import WaveEngine
from src_v2.tools.embedding import encode_query, warmup
from src_v2.rules.safety_engine import SafetyEngine
from src_v2.tools.search_exercises import search_exercises

# 初始化
cfg = get_config()
data = DataStore(config=cfg.data)
asyncio.run(data.load())
engine = WaveEngine(data_store=data, config=cfg.engine)
safety = SafetyEngine(graph_store=data.graph, metadata_store=data.metadata)
warmup()

# 端到端测试
queries = [
    "练胸的动作",
    "适合新手的背部训练",
    "腰椎间盘突出可以做什么运动",
    "高蛋白低脂肪的食物",
]

for q in queries:
    t0 = time.time()
    result = asyncio.run(search_exercises(
        query_text=q,
        user_profile={"fitness_level": "intermediate"},
        top_k=5,
        wave_engine=engine,
        safety_engine=safety,
    ))
    elapsed = (time.time() - t0) * 1000
    
    print(f"\n查询: {q} ({elapsed:.0f}ms)")
    for ex in result["exercises"][:5]:
        score = ex["score"]
        name = ex.get("name_zh", ex.get("name", ""))
        print(f"  [{score:.3f}] {name}")

# 知识搜索测试
from src_v2.tools.knowledge_and_food import search_knowledge, search_foods

print("\n\n=== 知识搜索 ===")
t0 = time.time()
kr = asyncio.run(search_knowledge("渐进超负荷原则", top_k=3, wave_engine=engine))
elapsed = (time.time() - t0) * 1000
print(f"查询: 渐进超负荷原则 ({elapsed:.0f}ms)")
for item in kr["results"]:
    title = item["title"][:30]
    print(f"  [{item['score']:.3f}] {title}")

print("\n=== 食物搜索 ===")
t0 = time.time()
fr = asyncio.run(search_foods("高蛋白食物", top_k=5, wave_engine=engine))
elapsed = (time.time() - t0) * 1000
print(f"查询: 高蛋白食物 ({elapsed:.0f}ms)")
for item in fr["foods"]:
    name = item["name"]
    protein = item["protein"]
    print(f"  [{item['score']:.3f}] {name} (蛋白质: {protein}g)")
