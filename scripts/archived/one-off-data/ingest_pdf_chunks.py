#!/usr/bin/env python3
"""
PDF Chunks向量化入库脚本
读取parse_pdf_textbooks.py生成的JSON chunks，向量化后写入Qdrant training_knowledge集合

用法:
  # dry-run
  docker exec fitness_daml_rag python /app/scripts/ingest_pdf_chunks.py --dry-run

  # 正式入库
  docker exec fitness_daml_rag python /app/scripts/ingest_pdf_chunks.py

版本: v1.0.0
"""

import os, sys, json, hashlib, time, logging, argparse
from pathlib import Path
from typing import List

if sys.platform == 'win32':
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

COLLECTION_NAME = "training_knowledge"
VECTOR_DIM = 1024
EMBEDDING_MODEL = "thenlper/gte-large-zh"
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
DEFAULT_INPUT_DIR = "/app/scripts/data/pdf_chunks/json"
BATCH_SIZE = 32
UPSERT_BATCH = 100


def main():
    parser = argparse.ArgumentParser(description='PDF Chunks向量化入库')
    parser.add_argument('--input-dir', default=DEFAULT_INPUT_DIR)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        return 1

    json_files = sorted(input_dir.glob('*.json'))
    logger.info(f"找到 {len(json_files)} 个JSON文件")

    # 加载所有chunks
    all_chunks = []
    for jf in json_files:
        data = json.loads(jf.read_text(encoding='utf-8'))
        chunks = data.get('chunks', [])
        logger.info(f"  {jf.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    logger.info(f"总计: {len(all_chunks)} chunks")

    if args.dry_run:
        total_chars = sum(len(c['text']) for c in all_chunks)
        logger.info(f"DRY-RUN: {len(all_chunks)} chunks, {total_chars:,} chars")
        return 0

    # 初始化Embedding模型
    logger.info(f"加载Embedding模型: {EMBEDDING_MODEL}")
    from sentence_transformers import SentenceTransformer
    encoder = SentenceTransformer(EMBEDDING_MODEL)
    test_vec = encoder.encode("test")
    logger.info(f"模型加载成功，维度: {len(test_vec)}")

    # 初始化Qdrant
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, Distance, VectorParams
    client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)

    collections = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in collections:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
        )
        logger.info(f"创建集合: {COLLECTION_NAME}")
    else:
        info = client.get_collection(COLLECTION_NAME)
        logger.info(f"集合已存在: {COLLECTION_NAME} ({info.points_count} points)")

    # 批量向量化 + 入库
    start_time = time.time()
    total_upserted = 0

    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i:i + BATCH_SIZE]
        texts = [c['text'] for c in batch]
        vectors = encoder.encode(texts, show_progress_bar=False).tolist()

        points = []
        for chunk, vector in zip(batch, vectors):
            meta = chunk.get('metadata', {})
            point_id = hashlib.md5(chunk['chunk_id'].encode()).hexdigest()[:32]
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    'source': meta.get('source', 'pdf_textbook'),
                    'filename': meta.get('filename', ''),
                    'title': meta.get('title', ''),
                    'chapter': meta.get('chapter', ''),
                    'page_start': meta.get('page_start', 0),
                    'page_end': meta.get('page_end', 0),
                    'chunk_index': meta.get('chunk_index', 0),
                    'language': meta.get('language', 'en'),
                    'char_count': meta.get('char_count', len(chunk['text'])),
                    'total_chunks': meta.get('total_chunks', 0),
                    'chunk_text': chunk['text'],
                }
            ))

        # 分批upsert
        for j in range(0, len(points), UPSERT_BATCH):
            sub = points[j:j + UPSERT_BATCH]
            client.upsert(collection_name=COLLECTION_NAME, points=sub)

        total_upserted += len(batch)
        if (i // BATCH_SIZE) % 10 == 0:
            logger.info(f"  进度: {total_upserted}/{len(all_chunks)}")

    elapsed = time.time() - start_time
    info = client.get_collection(COLLECTION_NAME)

    logger.info("=" * 60)
    logger.info(f"PDF入库完成")
    logger.info(f"  写入: {total_upserted} chunks")
    logger.info(f"  耗时: {elapsed:.1f}s")
    logger.info(f"  集合总量: {info.points_count} points")
    logger.info("=" * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
