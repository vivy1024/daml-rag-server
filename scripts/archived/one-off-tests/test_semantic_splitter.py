#!/usr/bin/env python3
"""Quick test for SemanticSplitter"""
import sys
import time
sys.path.insert(0, '/app/scripts')

from semantic_splitter import SemanticSplitter

text = (
    "深蹲是一个非常重要的复合动作，它可以锻炼到股四头肌、臀大肌和腘绳肌。"
    "正确的深蹲姿势要求双脚与肩同宽，脚尖略微外展。"
    "下蹲时膝盖应该沿着脚尖方向移动，不要内扣。"
    "核心肌群需要保持收紧，脊柱保持中立位。"
    "蛋白质是肌肉修复和生长的关键营养素。"
    "一般建议力量训练者每天摄入1.6到2.2克每公斤体重的蛋白质。"
    "优质蛋白质来源包括鸡胸肉、鸡蛋、牛奶和豆制品。"
    "训练后30分钟内补充蛋白质可以促进肌肉恢复。"
)

print(f"Input text length: {len(text)} chars")
print(f"Loading model...")

start = time.time()
splitter = SemanticSplitter(similarity_threshold=0.5)
results = splitter.split_with_metadata(text)
elapsed = time.time() - start

print(f"Split time: {elapsed:.2f}s")
print(f"Chunks: {len(results)}")
for i, r in enumerate(results):
    print(f"\nChunk {i+1}: {len(r['text'])} chars, sentences={r['sentence_count']}, avg_sim={r['avg_similarity']:.3f}")
    print(f"  {r['text'][:120]}")

print("\nSUCCESS")
