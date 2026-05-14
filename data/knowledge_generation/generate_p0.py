"""
知识库批量生成脚本 — P0 解剖学+体态+康复

运行方式:
  python data/knowledge_generation/generate_p0.py

输出: data/knowledge_generation/output/ 下的 JSON 文件
每个文件包含一个类别的所有 chunks，可直接用 embedding pipeline 导入。
"""

import json
import os
from typing import List, Dict

from chunk_utils import make_chunk
from anatomy_muscles import generate_anatomy_muscles
from posture_corrections import generate_posture_corrections
from rehabilitation import generate_rehabilitation
from methodology import generate_methodology
from nutrition import generate_nutrition
from recovery import generate_recovery

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)


def main():
    all_chunks = []
    all_chunks.extend(generate_anatomy_muscles())
    all_chunks.extend(generate_posture_corrections())
    all_chunks.extend(generate_rehabilitation())
    all_chunks.extend(generate_methodology())
    all_chunks.extend(generate_nutrition())
    all_chunks.extend(generate_recovery())

    # 按类别分文件输出
    by_category = {}
    for chunk in all_chunks:
        cat = chunk["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(chunk)

    for cat, chunks in by_category.items():
        path = os.path.join(OUTPUT_DIR, f"{cat}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)
        print(f"  {cat}: {len(chunks)} chunks -> {path}")

    print(f"\n总计: {len(all_chunks)} chunks")


if __name__ == "__main__":
    main()
