# -*- coding: utf-8 -*-
"""
知识库批量入库脚本

从 docs/knowledge/ 目录读取 Markdown 知识文章，
解析 YAML front matter，写入 MySQL + Qdrant + Neo4j 三端。

用法:
    docker exec fitness_daml_rag python scripts/import_knowledge.py [--dry-run] [--dir docs/knowledge]

版本: v1.0.0
日期: 2026-02-21
"""

import os
import sys
import re
import json
import yaml
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# 添加项目根目录到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def parse_markdown_article(filepath: str) -> Optional[Dict[str, Any]]:
    """
    解析带 YAML front matter 的 Markdown 知识文章。

    Returns:
        dict with keys: meta (YAML), content (正文), summary (摘要段落)
        None if parsing fails
    """
    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    # 解析 YAML front matter (--- ... ---)
    fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not fm_match:
        logger.warning(f"⚠️ 无 YAML front matter: {filepath}")
        return None

    try:
        meta = yaml.safe_load(fm_match.group(1))
    except yaml.YAMLError as e:
        logger.error(f"❌ YAML 解析失败: {filepath}: {e}")
        return None

    content = fm_match.group(2).strip()

    # 提取摘要段落（## 摘要 下的内容）
    summary_match = re.search(r"## 摘要\s*\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    summary = summary_match.group(1).strip() if summary_match else content[:200]

    return {
        "meta": meta,
        "content": content,
        "summary": summary,
        "filepath": filepath,
    }


def import_to_mysql(article: Dict[str, Any], db_config: Dict[str, str], dry_run: bool = False) -> Optional[int]:
    """写入 MySQL knowledge_articles + knowledge_references 表"""
    import pymysql

    meta = article["meta"]

    conn = pymysql.connect(
        host=db_config["host"],
        port=int(db_config["port"]),
        user=db_config["user"],
        password=db_config["password"],
        database=db_config["database"],
        charset="utf8mb4",
    )

    try:
        with conn.cursor() as cursor:
            # 查找 category_id by slug
            category_slug = meta.get("category", "")
            cursor.execute(
                "SELECT id FROM knowledge_categories WHERE slug = %s", (category_slug,)
            )
            row = cursor.fetchone()
            if not row:
                logger.warning(f"⚠️ 分类不存在: {category_slug}，跳过")
                return None
            category_id = row[0]

            # 检查是否已存在（按 title 去重）
            title = meta.get("title", "")
            cursor.execute(
                "SELECT id FROM knowledge_articles WHERE title = %s", (title,)
            )
            existing = cursor.fetchone()
            if existing:
                logger.info(f"⏭️ 已存在: {title} (id={existing[0]})")
                return existing[0]

            if dry_run:
                logger.info(f"[DRY-RUN] MySQL: {title} → category={category_slug}")
                return -1

            # 插入文章
            tags_json = json.dumps(meta.get("tags", []), ensure_ascii=False)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """INSERT INTO knowledge_articles
                (title, summary, content, category_id, source_book, source_chapter,
                 source_page, tags, status, difficulty, view_count, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0, %s, %s)""",
                (
                    title,
                    article["summary"],
                    article["content"],
                    category_id,
                    meta.get("source_book"),
                    meta.get("source_chapter"),
                    meta.get("source_page"),
                    tags_json,
                    meta.get("status", "draft"),
                    meta.get("difficulty", "intermediate"),
                    now,
                    now,
                ),
            )
            article_id = cursor.lastrowid

            # 插入引用
            for ref in meta.get("references", []):
                cursor.execute(
                    """INSERT INTO knowledge_references
                    (article_id, ref_type, title, authors, year, doi, chapter, page_range, isbn, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                    (
                        article_id,
                        ref.get("type", "book"),
                        ref.get("title", ""),
                        ref.get("authors"),
                        ref.get("year"),
                        ref.get("doi"),
                        ref.get("chapter"),
                        ref.get("page_range"),
                        ref.get("isbn"),
                        now,
                        now,
                    ),
                )

            conn.commit()
            logger.info(f"✅ MySQL: {title} (id={article_id}, refs={len(meta.get('references', []))})")
            return article_id

    except pymysql.Error as e:
        conn.rollback()
        logger.error(f"❌ MySQL 写入失败: {e}")
        return None
    finally:
        conn.close()


def import_to_qdrant(
    article: Dict[str, Any],
    article_id: int,
    qdrant_host: str,
    qdrant_port: int,
    encoder,
    collection: str = "knowledge_articles",
    dry_run: bool = False,
) -> bool:
    """向量化写入 Qdrant"""
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance

    meta = article["meta"]
    # 用 title + summary 作为向量化文本（检索时最相关的部分）
    embed_text = f"{meta.get('title', '')}。{article['summary']}"

    if dry_run:
        logger.info(f"[DRY-RUN] Qdrant: id={article_id}, text={embed_text[:50]}...")
        return True

    client = QdrantClient(host=qdrant_host, port=qdrant_port, timeout=30)

    # 确保 collection 存在
    collections = [c.name for c in client.get_collections().collections]
    if collection not in collections:
        client.create_collection(
            collection_name=collection,
            vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
        )
        logger.info(f"📦 创建 Qdrant collection: {collection}")

    # 向量化
    vector = encoder.encode(embed_text).tolist()

    # 写入
    client.upsert(
        collection_name=collection,
        points=[
            PointStruct(
                id=article_id,
                vector=vector,
                payload={
                    "article_id": article_id,
                    "title": meta.get("title", ""),
                    "category": meta.get("category", ""),
                    "source_book": meta.get("source_book", ""),
                    "tags": meta.get("tags", []),
                    "difficulty": meta.get("difficulty", "intermediate"),
                    "summary": article["summary"][:500],
                },
            )
        ],
    )
    logger.info(f"✅ Qdrant: id={article_id}, dim={len(vector)}")
    return True


def import_to_neo4j(
    article: Dict[str, Any],
    article_id: int,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    dry_run: bool = False,
) -> bool:
    """创建 Neo4j KnowledgeArticle 节点"""
    from neo4j import GraphDatabase

    meta = article["meta"]

    if dry_run:
        logger.info(f"[DRY-RUN] Neo4j: KnowledgeArticle id={article_id}")
        return True

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    try:
        with driver.session() as session:
            # 创建或更新 KnowledgeArticle 节点
            session.run(
                """MERGE (ka:KnowledgeArticle {article_id: $article_id})
                SET ka.title = $title,
                    ka.category = $category,
                    ka.source_book = $source_book,
                    ka.difficulty = $difficulty,
                    ka.tags = $tags,
                    ka.updated_at = datetime()""",
                article_id=article_id,
                title=meta.get("title", ""),
                category=meta.get("category", ""),
                source_book=meta.get("source_book", ""),
                difficulty=meta.get("difficulty", "intermediate"),
                tags=meta.get("tags", []),
            )

            # 尝试关联已有的 Exercise/Muscle/Food 节点（基于标签匹配）
            for tag in meta.get("tags", []):
                # 关联肌群
                session.run(
                    """MATCH (ka:KnowledgeArticle {article_id: $article_id})
                    MATCH (m:Muscle) WHERE m.name_cn CONTAINS $tag OR m.name CONTAINS $tag
                    MERGE (ka)-[:RELATES_TO]->(m)""",
                    article_id=article_id,
                    tag=tag,
                )

        logger.info(f"✅ Neo4j: KnowledgeArticle id={article_id}")
        return True

    except Exception as e:
        logger.error(f"❌ Neo4j 写入失败: {e}")
        return False
    finally:
        driver.close()


def scan_knowledge_dir(base_dir: str) -> List[str]:
    """扫描知识目录，返回所有 .md 文件路径（排除 TEMPLATE.md）"""
    files = []
    for root, _, filenames in os.walk(base_dir):
        for fn in sorted(filenames):
            if fn.endswith(".md") and fn != "TEMPLATE.md":
                files.append(os.path.join(root, fn))
    return files


def main():
    parser = argparse.ArgumentParser(description="知识库批量入库")
    parser.add_argument("--dir", default="docs/knowledge", help="知识文章目录")
    parser.add_argument("--dry-run", action="store_true", help="仅解析不写入")
    parser.add_argument("--skip-qdrant", action="store_true", help="跳过 Qdrant 写入")
    parser.add_argument("--skip-neo4j", action="store_true", help="跳过 Neo4j 写入")
    args = parser.parse_args()

    # 配置
    db_config = {
        "host": os.getenv("MYSQL_HOST", "mysql"),
        "port": os.getenv("MYSQL_PORT", "3306"),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", ""),
        "database": os.getenv("MYSQL_DATABASE", "yuzhen_fitness"),
    }
    qdrant_host = os.getenv("QDRANT_HOST", "qdrant")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))
    neo4j_uri = os.getenv("NEO4J_URI", "bolt://neo4j:7687")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")

    # 扫描文件
    files = scan_knowledge_dir(args.dir)
    logger.info(f"📂 扫描到 {len(files)} 篇知识文章")

    if not files:
        logger.warning("⚠️ 未找到知识文章，请检查目录路径")
        return

    # 加载 embedding 模型（仅在需要 Qdrant 时）
    encoder = None
    if not args.skip_qdrant and not args.dry_run:
        logger.info("🔄 加载 GTE-Large-zh 模型...")
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv("EMBEDDING_MODEL", "thenlper/gte-large-zh")
        encoder = SentenceTransformer(model_name)
        logger.info(f"✅ 模型加载完成: {model_name}")

    # 统计
    stats = {"total": len(files), "mysql_ok": 0, "qdrant_ok": 0, "neo4j_ok": 0, "skipped": 0, "failed": 0}

    for filepath in files:
        logger.info(f"\n{'='*60}")
        logger.info(f"📄 处理: {filepath}")

        article = parse_markdown_article(filepath)
        if not article:
            stats["failed"] += 1
            continue

        # MySQL
        article_id = import_to_mysql(article, db_config, dry_run=args.dry_run)
        if article_id is None:
            stats["failed"] += 1
            continue
        if article_id == -1:  # dry-run
            stats["mysql_ok"] += 1
            continue

        stats["mysql_ok"] += 1

        # Qdrant
        if not args.skip_qdrant:
            if import_to_qdrant(article, article_id, qdrant_host, qdrant_port, encoder, dry_run=args.dry_run):
                stats["qdrant_ok"] += 1

        # Neo4j
        if not args.skip_neo4j:
            if import_to_neo4j(article, article_id, neo4j_uri, neo4j_user, neo4j_password, dry_run=args.dry_run):
                stats["neo4j_ok"] += 1

    # 汇总
    logger.info(f"\n{'='*60}")
    logger.info(f"📊 入库完成:")
    logger.info(f"   总计: {stats['total']} 篇")
    logger.info(f"   MySQL: {stats['mysql_ok']} ✅")
    logger.info(f"   Qdrant: {stats['qdrant_ok']} ✅")
    logger.info(f"   Neo4j: {stats['neo4j_ok']} ✅")
    logger.info(f"   跳过: {stats['skipped']}, 失败: {stats['failed']}")


if __name__ == "__main__":
    main()
