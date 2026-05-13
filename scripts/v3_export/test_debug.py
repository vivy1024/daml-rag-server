"""调试：检查返回结果的数据结构"""
import os, asyncio, json
os.environ["DATA_DIR"] = "/app/data/v3"

from src_v2.config import get_config
from src_v2.data.loader import DataStore
from src_v2.engine.wave_engine import WaveEngine
from src_v2.tools.embedding import warmup
from src_v2.rules.safety_engine import SafetyEngine
from src_v2.tools.search_exercises import search_exercises

cfg = get_config()
data = DataStore(config=cfg.data)
asyncio.run(data.load())
engine = WaveEngine(data_store=data, config=cfg.engine)
safety = SafetyEngine(graph_store=data.graph, metadata_store=data.metadata)
warmup()

result = asyncio.run(search_exercises(
    query_text="练胸的动作",
    user_profile={"fitness_level": "intermediate"},
    top_k=3,
    wave_engine=engine,
    safety_engine=safety,
))

# 打印完整结构
print(json.dumps(result["exercises"][:2], ensure_ascii=False, indent=2))

# 也看看 payload 里有什么
print("\n\n=== 第一个 exercise payload ===")
print(json.dumps(data.exercise_payloads[0], ensure_ascii=False, indent=2)[:500])
