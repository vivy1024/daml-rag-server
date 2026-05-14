#!/usr/bin/env python3
"""
健身教材Markdown知识入库脚本
将73个B站字幕Markdown文件通过语义分割后向量化入库到Qdrant training_knowledge集合

用法:
  # dry-run模式（只统计不入库）
  docker exec fitness_daml_rag python /app/scripts/ingest_markdown_knowledge.py --dry-run

  # 正式入库
  docker exec fitness_daml_rag python /app/scripts/ingest_markdown_knowledge.py

  # 指定输入目录
  docker exec fitness_daml_rag python /app/scripts/ingest_markdown_knowledge.py --input-dir /app/knowledge_texts

版本: v1.0.0
作者: 薛小川
日期: 2026-02-16
"""

import os
import sys
import json
import re
import logging
import argparse
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field, asdict

# Windows encoding fix
if sys.platform == 'win32':
    for stream in [sys.stdout, sys.stderr]:
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# ─── 配置 ───────────────────────────────────────────────

COLLECTION_NAME = "training_knowledge"
VECTOR_DIM = 1024
EMBEDDING_MODEL = "thenlper/gte-large-zh"
QDRANT_HOST = os.getenv("QDRANT_HOST", "qdrant")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Chunk参数（基于调研结论：LlamaIndex SemanticSplitter思路）
CHUNK_SIZE = 800        # 目标chunk大小（字符）
CHUNK_OVERLAP = 150     # 重叠大小
MIN_CHUNK_SIZE = 100    # 最小chunk大小（过短的丢弃）

DEFAULT_INPUT_DIR = "/app/scripts/data/knowledge_texts"
CHECKPOINT_FILE = "/app/scripts/.ingest_checkpoint.json"


# ─── 数据结构 ─────────────────────────────────────────────

@dataclass
class MarkdownMeta:
    source: str = ""
    bvid: str = ""
    title: str = ""
    category: str = ""
    duration: str = ""
    download_date: str = ""
    paragraph_count: int = 0


@dataclass
class Chunk:
    text: str
    metadata: Dict = field(default_factory=dict)
    chunk_id: str = ""

    def __post_init__(self):
        if not self.chunk_id:
            h = hashlib.md5(f"{self.metadata.get('bvid','')}-{self.metadata.get('chunk_index',0)}-{self.text[:50]}".encode()).hexdigest()[:12]
            self.chunk_id = f"tk_{h}"


# ─── Markdown解析 ─────────────────────────────────────────

def parse_frontmatter(content: str) -> Tuple[MarkdownMeta, str]:
    """解析YAML frontmatter"""
    meta = MarkdownMeta()
    body = content

    fm_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body = content[fm_match.end():]
        for line in fm_text.strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                key, val = key.strip(), val.strip()
                if hasattr(meta, key):
                    if key == 'paragraph_count':
                        try:
                            setattr(meta, key, int(val))
                        except ValueError:
                            pass
                    else:
                        setattr(meta, key, val)
    return meta, body


def split_into_paragraphs(body: str) -> List[Dict]:
    """按段落标记分割（## 段落N (HH:MM:SS - HH:MM:SS)）"""
    pattern = r'##\s*段落(\d+)\s*\(([^)]+)\)'
    parts = re.split(pattern, body)

    paragraphs = []
    if len(parts) < 4:
        # 没有段落标记，整体作为一个段落
        text = body.strip()
        if text:
            # 去掉标题行
            lines = text.split('\n')
            text_lines = [l for l in lines if not l.startswith('# ')]
            paragraphs.append({
                'index': 1,
                'timestamp': '00:00:00 - 00:00:00',
                'text': '\n'.join(text_lines).strip()
            })
        return paragraphs

    # parts: [before, idx1, ts1, text1, idx2, ts2, text2, ...]
    for i in range(1, len(parts), 3):
        if i + 2 < len(parts):
            idx = int(parts[i])
            timestamp = parts[i + 1].strip()
            text = parts[i + 2].strip()
            if text:
                paragraphs.append({
                    'index': idx,
                    'timestamp': timestamp,
                    'text': text
                })

    return paragraphs


# ─── 语义Chunk ──────────────────────────────────────────

def semantic_chunk(text: str, max_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """语义分割：优先按句子边界分割，保持语义完整性"""
    if len(text) <= max_size:
        return [text] if len(text) >= MIN_CHUNK_SIZE else []

    # 分句（中文句号、问号、感叹号、换行）
    sentences = re.split(r'(?<=[。！？\n])', text)
    sentences = [s.strip() for s in sentences if s.strip()]

    chunks = []
    current = ""

    for sent in sentences:
        if len(current) + len(sent) <= max_size:
            current += sent
        else:
            if current and len(current) >= MIN_CHUNK_SIZE:
                chunks.append(current)
            # 重叠：取上一个chunk的尾部
            if overlap > 0 and current:
                tail = current[-overlap:]
                current = tail + sent
            else:
                current = sent

    # 最后一个chunk
    if current and len(current) >= MIN_CHUNK_SIZE:
        chunks.append(current)
    elif current and chunks:
        # 太短就合并到上一个
        chunks[-1] += current

    return chunks


def process_markdown_file(filepath: Path) -> List[Chunk]:
    """处理单个Markdown文件，返回chunk列表"""
    content = filepath.read_text(encoding='utf-8')
    meta, body = parse_frontmatter(content)
    paragraphs = split_into_paragraphs(body)

    all_chunks = []
    chunk_idx = 0

    for para in paragraphs:
        text_chunks = semantic_chunk(para['text'])

        ts_parts = para['timestamp'].split(' - ')
        ts_start = ts_parts[0].strip() if len(ts_parts) > 0 else ""
        ts_end = ts_parts[1].strip() if len(ts_parts) > 1 else ""

        for text in text_chunks:
            chunk = Chunk(
                text=text,
                metadata={
                    'source': 'bilibili_subtitle',
                    'bvid': meta.bvid,
                    'title': meta.title,
                    'category': meta.category,
                    'paragraph_index': para['index'],
                    'timestamp_start': ts_start,
                    'timestamp_end': ts_end,
                    'chunk_index': chunk_idx,
                    'char_count': len(text),
                    'duration': meta.duration,
                }
            )
            all_chunks.append(chunk)
            chunk_idx += 1

    # 回填total_chunks
    for c in all_chunks:
        c.metadata['total_chunks'] = len(all_chunks)

    return all_chunks


# ─── 向量化 + 入库 ────────────────────────────────────────

class KnowledgeIngester:
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.encoder = None
        self.qdrant = None

        if not dry_run:
            self._init_encoder()
            self._init_qdrant()

    def _init_encoder(self):
        logger.info(f"加载Embedding模型: {EMBEDDING_MODEL}")
        try:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer(EMBEDDING_MODEL)
            test_vec = self.encoder.encode("test")
            logger.info(f"Embedding模型加载成功，维度: {len(test_vec)}")
        except Exception as e:
            logger.error(f"Embedding模型加载失败: {e}")
            raise

    def _init_qdrant(self):
        logger.info(f"连接Qdrant: {QDRANT_HOST}:{QDRANT_PORT}")
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams
            self.qdrant = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT, timeout=30)

            # 确保集合存在
            collections = [c.name for c in self.qdrant.get_collections().collections]
            if COLLECTION_NAME not in collections:
                logger.info(f"创建集合: {COLLECTION_NAME}")
                self.qdrant.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE)
                )
            else:
                info = self.qdrant.get_collection(COLLECTION_NAME)
                logger.info(f"集合已存在: {COLLECTION_NAME} ({info.points_count} points)")
        except Exception as e:
            logger.error(f"Qdrant连接失败: {e}")
            raise

    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """批量向量化"""
        all_vectors = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            vectors = self.encoder.encode(batch, show_progress_bar=False)
            all_vectors.extend(vectors.tolist())
        return all_vectors

    def upsert_chunks(self, chunks: List[Chunk]):
        """批量写入Qdrant"""
        if not chunks:
            return

        from qdrant_client.models import PointStruct

        texts = [c.text for c in chunks]
        vectors = self.encode_batch(texts)

        points = []
        for chunk, vector in zip(chunks, vectors):
            point = PointStruct(
                id=hashlib.md5(chunk.chunk_id.encode()).hexdigest()[:32],
                vector=vector,
                payload={
                    **chunk.metadata,
                    'chunk_text': chunk.text,
                }
            )
            points.append(point)

        # 分批upsert（每批100个）
        for i in range(0, len(points), 100):
            batch = points[i:i + 100]
            self.qdrant.upsert(collection_name=COLLECTION_NAME, points=batch)

    def ingest_file(self, filepath: Path) -> int:
        """处理并入库单个文件，返回chunk数"""
        chunks = process_markdown_file(filepath)
        if not chunks:
            return 0

        if not self.dry_run:
            self.upsert_chunks(chunks)

        return len(chunks)


# ─── 断点续传 ─────────────────────────────────────────────

def load_checkpoint(path: str) -> Dict:
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {'processed': {}, 'version': '1.0'}


def save_checkpoint(path: str, data: Dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ─── 主流程 ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='健身教材Markdown知识入库')
    parser.add_argument('--input-dir', default=DEFAULT_INPUT_DIR, help='Markdown文件目录')
    parser.add_argument('--dry-run', action='store_true', help='只统计不入库')
    parser.add_argument('--force', action='store_true', help='忽略checkpoint，重新处理所有文件')
    parser.add_argument('--checkpoint', default=CHECKPOINT_FILE, help='断点文件路径')
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    if not input_dir.exists():
        logger.error(f"输入目录不存在: {input_dir}")
        logger.info("提示: 确认docker-compose.yml已挂载 knowledge_texts 目录")
        return 1

    # 收集MD文件
    md_files = sorted([f for f in input_dir.glob('*.md') if f.name != 'README.md'])
    logger.info(f"找到 {len(md_files)} 个Markdown文件")

    if not md_files:
        logger.warning("无文件可处理")
        return 0

    # 断点续传
    checkpoint = load_checkpoint(args.checkpoint) if not args.force else {'processed': {}, 'version': '1.0'}

    # 初始化
    ingester = KnowledgeIngester(dry_run=args.dry_run)

    total_chunks = 0
    total_chars = 0
    processed = 0
    skipped = 0
    failed = 0
    start_time = time.time()

    for i, filepath in enumerate(md_files, 1):
        fname = filepath.name

        # 检查checkpoint
        if fname in checkpoint['processed']:
            skipped += 1
            total_chunks += checkpoint['processed'][fname].get('chunks', 0)
            continue

        try:
            chunk_count = ingester.ingest_file(filepath)
            total_chunks += chunk_count

            # 统计字符数
            content = filepath.read_text(encoding='utf-8')
            chars = len(content)
            total_chars += chars

            # 更新checkpoint
            checkpoint['processed'][fname] = {
                'chunks': chunk_count,
                'chars': chars,
                'status': 'success',
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
            }
            if not args.dry_run:
                save_checkpoint(args.checkpoint, checkpoint)

            processed += 1
            mode = "DRY-RUN" if args.dry_run else "INGESTED"
            logger.info(f"[{i}/{len(md_files)}] {mode}: {fname} → {chunk_count} chunks ({chars} chars)")

        except Exception as e:
            failed += 1
            logger.error(f"[{i}/{len(md_files)}] FAILED: {fname} → {e}")

    elapsed = time.time() - start_time

    logger.info("=" * 60)
    logger.info(f"{'DRY-RUN 统计' if args.dry_run else '入库完成'}")
    logger.info(f"  处理: {processed} | 跳过: {skipped} | 失败: {failed}")
    logger.info(f"  总chunks: {total_chunks} | 总字符: {total_chars:,}")
    logger.info(f"  耗时: {elapsed:.1f}s")
    if not args.dry_run and total_chunks > 0:
        logger.info(f"  Qdrant集合: {COLLECTION_NAME}")
    logger.info("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
