#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义Chunk重新入库脚本

使用SemanticSplitter替换原有固定大小分割，重新处理所有知识文件并入库Qdrant。

功能：
1. 读取74个MD文件 + 4个PDF的JSON chunks
2. 用SemanticSplitter重新分割
3. 清空Qdrant training_knowledge集合中的旧数据
4. 重新入库新的语义chunks
5. 输出对比报告

用法:
  # dry-run（只统计不入库）
  docker exec fitness_daml_rag python /app/scripts/reingest_with_semantic_chunks.py --dry-run

  # 只处理MD文件
  docker exec fitness_daml_rag python /app/scripts/reingest_with_semantic_chunks.py --source md --dry-run

  # 只处理PDF文件
  docker exec fitness_daml_rag python /app/scripts/reingest_with_semantic_chunks.py --source pdf --dry-run

  # 正式入库（全部）
  docker exec fitness_daml_rag python /app/scripts/reingest_with_semantic_chunks.py --source all

  # 自定义阈值
  docker exec fitness_daml_rag python /app/scripts/reingest_with_semantic_chunks.py --threshold 0.45 --dry-run

版本: v1.0.0
日期: 2026-02-16
作者: 薛小川
"""

import os
import sys
import re
import json
import hashlib
import time
import logging
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field

# Windows encoding fix
if sys.platform == "win32":
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

# ─── 配置 ───────────────────────────────────────────────

COLLECTION_NAME = "training_knowledge"
VECTOR_DIM = 1024
EMBEDDING_MODEL = "thenlper/gte-large-zh"
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

MD_INPUT_DIR = "/app/scripts/data/knowledge_texts"
PDF_INPUT_DIR = "/app/scripts/data/pdf_chunks/json"

UPSERT_BATCH = 100


# ─── MD文件解析（复用ingest_markdown_knowledge.py的逻辑）───

def parse_frontmatter(content: str) -> Tuple[Dict, str]:
    """解析YAML frontmatter"""
    meta = {}
    body = content

    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = content[fm_match.end():]
        for line in fm_text.strip().split("\n"):
            if ":" in line:
                key, val = line.split(":", 1)
                meta[key.strip()] = val.strip()
    return meta, body


def extract_md_text(filepath: Path) -> Tuple[Dict, str]:
    """从MD文件提取元数据和正文文本"""
    content = filepath.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(content)

    # 去掉段落标记行，只保留正文
    # 格式: ## 段落N (HH:MM:SS - HH:MM:SS)
    body = re.sub(r"##\s*段落\d+\s*\([^)]+\)\s*", "\n", body)
    # 去掉标题行
    body = re.sub(r"^#\s+.*$", "", body, flags=re.MULTILINE)
    body = body.strip()

    return meta, body


def extract_pdf_text(json_path: Path) -> Tuple[Dict, List[Dict]]:
    """从PDF JSON文件提取元数据和chunk列表"""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    file_meta = {
        "source_file": data.get("source_file", ""),
        "total_chunks": data.get("total_chunks", 0),
        "chunk_size": data.get("chunk_size", 0),
    }
    chunks = data.get("chunks", [])
    return file_meta, chunks


# ─── 主流程 ──────────────────────────────────────────────

def run(args):
    from semantic_splitter import SemanticSplitter

    splitter = SemanticSplitter(
        model_name=EMBEDDING_MODEL,
        similarity_threshold=args.threshold,
        max_chunk_size=args.max_chunk_size,
        min_chunk_size=args.min_chunk_size,
    )

    # ─── 收集源文件 ───
    md_files = []
    pdf_files = []

    if args.source in ("md", "all"):
        md_dir = Path(MD_INPUT_DIR)
        if md_dir.exists():
            md_files = sorted([f for f in md_dir.glob("*.md") if f.name != "README.md"])
            logger.info(f"MD文件: {len(md_files)} 个")
        else:
            logger.warning(f"MD目录不存在: {MD_INPUT_DIR}")

    if args.source in ("pdf", "all"):
        pdf_dir = Path(PDF_INPUT_DIR)
        if pdf_dir.exists():
            pdf_files = sorted(pdf_dir.glob("*.json"))
            logger.info(f"PDF JSON文件: {len(pdf_files)} 个")
        else:
            logger.warning(f"PDF目录不存在: {PDF_INPUT_DIR}")

    if not md_files and not pdf_files:
        logger.error("没有找到任何源文件")
        return 1

    # ─── 统计旧数据 ───
    old_stats = {"md_chunks": 0, "pdf_chunks": 0, "total": 0}

    # 统计旧MD chunks（用旧方法模拟）
    for f in md_files:
        meta, body = extract_md_text(f)
        # 旧方法：800字符固定分割
        if body:
            old_count = max(1, len(body) // 800)
            old_stats["md_chunks"] += old_count

    # 统计旧PDF chunks
    for f in pdf_files:
        data = json.loads(f.read_text(encoding="utf-8"))
        old_stats["pdf_chunks"] += len(data.get("chunks", []))

    old_stats["total"] = old_stats["md_chunks"] + old_stats["pdf_chunks"]

    # ─── 语义分割 ───
    all_new_chunks = []  # [(text, metadata), ...]
    new_stats = {"md_chunks": 0, "pdf_chunks": 0, "total": 0}
    file_reports = []

    # 处理MD文件
    logger.info("=" * 60)
    logger.info("开始语义分割...")
    logger.info("=" * 60)

    for i, filepath in enumerate(md_files, 1):
        meta, body = extract_md_text(filepath)
        if not body or len(body) < 50:
            logger.warning(f"[{i}/{len(md_files)}] 跳过空文件: {filepath.name}")
            continue

        chunks = splitter.split_with_metadata(body)
        new_stats["md_chunks"] += len(chunks)

        bvid = meta.get("bvid", filepath.stem)
        title = meta.get("title", filepath.stem)
        category = meta.get("category", "")

        for ci, chunk in enumerate(chunks):
            chunk_id = f"sem_md_{bvid}_{ci:04d}"
            all_new_chunks.append((
                chunk["text"],
                {
                    "source": "bilibili_subtitle",
                    "bvid": bvid,
                    "title": title,
                    "category": category,
                    "chunk_index": ci,
                    "char_count": len(chunk["text"]),
                    "total_chunks": len(chunks),
                    "sentence_count": chunk["sentence_count"],
                    "avg_similarity": round(chunk["avg_similarity"], 4),
                    "splitter": "semantic_v1",
                    "threshold": args.threshold,
                    "chunk_id": chunk_id,
                },
            ))

        file_reports.append({
            "file": filepath.name,
            "type": "md",
            "old_est": max(1, len(body) // 800),
            "new_count": len(chunks),
            "body_len": len(body),
        })

        if i % 10 == 0 or i == len(md_files):
            logger.info(f"  MD进度: {i}/{len(md_files)} | 累计chunks: {new_stats['md_chunks']}")

    # 处理PDF文件
    for i, filepath in enumerate(pdf_files, 1):
        file_meta, old_chunks = extract_pdf_text(filepath)
        if not old_chunks:
            continue

        # 将所有旧chunk的文本合并为完整文本，再重新语义分割
        # 按chapter分组合并
        chapters = {}
        for oc in old_chunks:
            ch = oc.get("metadata", {}).get("chapter", "unknown")
            chapters.setdefault(ch, []).append(oc["text"])

        pdf_new_chunks = []
        for ch_name, ch_texts in chapters.items():
            full_text = "\n\n".join(ch_texts)
            if len(full_text) < 50:
                continue
            chunks = splitter.split_with_metadata(full_text)
            pdf_new_chunks.extend([(ch_name, c) for c in chunks])

        new_stats["pdf_chunks"] += len(pdf_new_chunks)
        stem = filepath.stem.replace("_chunks", "")
        title = old_chunks[0].get("metadata", {}).get("title", stem) if old_chunks else stem

        for ci, (ch_name, chunk) in enumerate(pdf_new_chunks):
            chunk_id = f"sem_pdf_{stem}_{ci:04d}"
            all_new_chunks.append((
                chunk["text"],
                {
                    "source": "pdf_textbook",
                    "filename": file_meta.get("source_file", filepath.name),
                    "title": title,
                    "chapter": ch_name,
                    "chunk_index": ci,
                    "char_count": len(chunk["text"]),
                    "total_chunks": len(pdf_new_chunks),
                    "sentence_count": chunk["sentence_count"],
                    "avg_similarity": round(chunk["avg_similarity"], 4),
                    "language": "en",
                    "splitter": "semantic_v1",
                    "threshold": args.threshold,
                    "chunk_id": chunk_id,
                },
            ))

        file_reports.append({
            "file": filepath.name,
            "type": "pdf",
            "old_est": len(old_chunks),
            "new_count": len(pdf_new_chunks),
            "body_len": sum(len(oc["text"]) for oc in old_chunks),
        })

        logger.info(f"  PDF [{i}/{len(pdf_files)}] {filepath.name}: {len(old_chunks)} → {len(pdf_new_chunks)} chunks")

    new_stats["total"] = new_stats["md_chunks"] + new_stats["pdf_chunks"]

    # ─── 对比报告 ───
    logger.info("\n" + "=" * 60)
    logger.info("语义分割对比报告")
    logger.info("=" * 60)
    logger.info(f"  相似度阈值: {args.threshold}")
    logger.info(f"  Chunk大小范围: [{args.min_chunk_size}, {args.max_chunk_size}]")
    logger.info(f"  MD文件: {len(md_files)} 个")
    logger.info(f"  PDF文件: {len(pdf_files)} 个")
    logger.info("-" * 40)
    logger.info(f"  旧chunk数（估算）: {old_stats['total']}")
    logger.info(f"    MD: ~{old_stats['md_chunks']} | PDF: {old_stats['pdf_chunks']}")
    logger.info(f"  新chunk数（语义）: {new_stats['total']}")
    logger.info(f"    MD: {new_stats['md_chunks']} | PDF: {new_stats['pdf_chunks']}")
    logger.info(f"  变化: {new_stats['total'] - old_stats['total']:+d} ({new_stats['total']/max(old_stats['total'],1)*100:.1f}%)")

    if all_new_chunks:
        avg_size = sum(len(c[0]) for c in all_new_chunks) / len(all_new_chunks)
        logger.info(f"  平均chunk大小: {avg_size:.0f} 字符")
        sizes = [len(c[0]) for c in all_new_chunks]
        logger.info(f"  大小范围: [{min(sizes)}, {max(sizes)}]")
        avg_sim = sum(c[1]["avg_similarity"] for c in all_new_chunks) / len(all_new_chunks)
        logger.info(f"  平均组内相似度: {avg_sim:.4f}")

    logger.info("=" * 60)

    if args.dry_run:
        logger.info("[DRY-RUN] 不执行入库操作")
        # 输出前5个文件的详细报告
        logger.info("\n文件级详情（前20个）:")
        for r in file_reports[:20]:
            logger.info(f"  {r['file']}: {r['old_est']} → {r['new_count']} chunks ({r['body_len']} chars)")
        return 0

    # ─── 正式入库 ───
    logger.info("\n开始入库到Qdrant...")

    from sentence_transformers import SentenceTransformer
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, Distance, VectorParams

    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=60)

    # 获取旧集合信息
    try:
        old_info = client.get_collection(COLLECTION_NAME)
        old_point_count = old_info.points_count
        logger.info(f"旧集合: {COLLECTION_NAME} ({old_point_count} points)")
    except Exception:
        old_point_count = 0

    # 删除旧集合并重建
    logger.info(f"删除旧集合: {COLLECTION_NAME}")
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    logger.info(f"创建新集合: {COLLECTION_NAME}")
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
    )

    # 使用splitter内部已加载的模型进行编码
    encoder = splitter.model
    start_time = time.time()
    total_upserted = 0
    encode_batch_size = 32

    for i in range(0, len(all_new_chunks), encode_batch_size):
        batch = all_new_chunks[i:i + encode_batch_size]
        texts = [c[0] for c in batch]
        vectors = encoder.encode(texts, show_progress_bar=False, normalize_embeddings=False).tolist()

        points = []
        for (text, meta), vector in zip(batch, vectors):
            point_id = hashlib.md5(meta["chunk_id"].encode()).hexdigest()[:32]
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    **meta,
                    "chunk_text": text,
                },
            ))

        # 分批upsert
        for j in range(0, len(points), UPSERT_BATCH):
            sub = points[j:j + UPSERT_BATCH]
            client.upsert(collection_name=COLLECTION_NAME, points=sub)

        total_upserted += len(batch)
        if (i // encode_batch_size) % 20 == 0:
            logger.info(f"  入库进度: {total_upserted}/{len(all_new_chunks)}")

    elapsed = time.time() - start_time
    new_info = client.get_collection(COLLECTION_NAME)

    logger.info("\n" + "=" * 60)
    logger.info("入库完成!")
    logger.info("=" * 60)
    logger.info(f"  旧数据: {old_point_count} points")
    logger.info(f"  新数据: {new_info.points_count} points")
    logger.info(f"  变化: {new_info.points_count - old_point_count:+d}")
    logger.info(f"  耗时: {elapsed:.1f}s")
    logger.info(f"  速度: {total_upserted / max(elapsed, 0.1):.1f} chunks/s")
    logger.info("=" * 60)

    return 0


def main():
    parser = argparse.ArgumentParser(description="语义Chunk重新入库")
    parser.add_argument("--source", choices=["md", "pdf", "all"], default="all",
                        help="处理来源 (默认: all)")
    parser.add_argument("--threshold", type=float, default=0.5,
                        help="语义相似度阈值 (默认: 0.5)")
    parser.add_argument("--max-chunk-size", type=int, default=1500,
                        help="最大chunk大小 (默认: 1500)")
    parser.add_argument("--min-chunk-size", type=int, default=100,
                        help="最小chunk大小 (默认: 100)")
    parser.add_argument("--dry-run", action="store_true",
                        help="只统计不入库")
    args = parser.parse_args()

    return run(args)


if __name__ == "__main__":
    sys.exit(main())
