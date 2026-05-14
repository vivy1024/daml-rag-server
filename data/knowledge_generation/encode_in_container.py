"""
在容器内运行的编码脚本 — 读取 JSON chunks，编码为向量，输出到 /tmp

用法（在宿主机执行）：
  docker cp this_script.py fitness_daml_rag:/tmp/encode_chunks.py
  docker exec fitness_daml_rag bash -c 'python /tmp/encode_chunks.py'
  docker cp fitness_daml_rag:/tmp/new_vectors.npy ./
"""

import json
import sys
import time
import numpy as np
from sentence_transformers import SentenceTransformer

INPUT_FILE = "/tmp/chunks_to_encode.json"
OUTPUT_FILE = "/tmp/new_vectors.npy"

def main():
    print("Loading chunks...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        chunks = json.load(f)
    print(f"  Loaded {len(chunks)} chunks")

    # Build texts
    texts = []
    for chunk in chunks:
        text = f"{chunk['title']}\n{chunk['content']}"
        if len(text) > 1500:
            text = text[:1500]
        texts.append(text)

    # Load model
    print("Loading gte-large-zh model...")
    model = SentenceTransformer("thenlper/gte-large-zh", device="cuda")

    # Encode
    print(f"Encoding {len(texts)} texts...")
    t0 = time.time()
    vectors = model.encode(texts, batch_size=32, show_progress_bar=True)
    elapsed = time.time() - t0
    print(f"  Done: shape={vectors.shape}, time={elapsed:.1f}s")

    # Save
    np.save(OUTPUT_FILE, vectors.astype(np.float32))
    print(f"  Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
