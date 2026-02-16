#!/usr/bin/env python3
"""
摄入状态追踪器 — 借鉴 R2R IngestionStatus 模式

追踪知识文档从解析到向量入库的全生命周期状态，存储在 MySQL knowledge_ingestion_status 表。

用法:
    from ingestion_tracker import IngestionTracker

    tracker = IngestionTracker()

    # 检查文档是否已入库
    if tracker.is_completed(document_id):
        print("已入库，跳过")
        return

    # 标记开始处理
    tracker.mark_processing(document_id, filename, source_type)

    # 处理完成
    tracker.mark_completed(document_id, chunk_count=195, vector_count=195,
                           total_chars=150000, processing_time_ms=10300)

    # 处理失败
    tracker.mark_failed(document_id, error_message="Qdrant连接超时")

    # 查询状态
    status = tracker.get_status(document_id)
    all_docs = tracker.list_all(source_type='pdf_textbook')

    # 回填已有数据
    tracker.backfill_existing()

版本: v1.0.0
作者: 薛小川
日期: 2026-02-16
"""

import os
import sys
import hashlib
import json
import logging
import time
from datetime import datetime
from typing import Optional, Dict, List, Any

logger = logging.getLogger(__name__)

# ─── 工具函数 ─────────────────────────────────────────────


def generate_document_id(filepath: str) -> str:
    """生成文档唯一标识: MD5(filepath)"""
    return hashlib.md5(filepath.encode('utf-8')).hexdigest()


# ─── 追踪器 ──────────────────────────────────────────────


class IngestionTracker:
    """知识摄入状态追踪器"""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        self.host = host or os.getenv("MYSQL_HOST", "mysql")
        self.port = port or int(os.getenv("MYSQL_PORT", "3306"))
        self.database = database or os.getenv("MYSQL_DATABASE", "fitness_app")
        self.user = user or os.getenv("MYSQL_USER", "fitness_user")
        self.password = password or os.getenv("MYSQL_PASSWORD", "fitness_pass")
        self._conn = None

    # ─── 连接管理 ─────────────────────────────────────────

    def _get_conn(self):
        """获取 MySQL 连接（懒初始化 + 自动重连）"""
        import pymysql

        if self._conn is not None:
            try:
                self._conn.ping(reconnect=True)
                return self._conn
            except Exception:
                self._conn = None

        self._conn = pymysql.connect(
            host=self.host,
            port=self.port,
            database=self.database,
            user=self.user,
            password=self.password,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=True,
            connect_timeout=10,
        )
        return self._conn

    def close(self):
        """关闭连接"""
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
            self._conn = None

    # ─── 核心 CRUD ────────────────────────────────────────

    def is_completed(self, document_id: str) -> bool:
        """检查文档是否已成功入库"""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM knowledge_ingestion_status WHERE document_id = %s",
                    (document_id,),
                )
                row = cur.fetchone()
                return row is not None and row["status"] == "completed"
        except Exception as e:
            logger.warning(f"[IngestionTracker] is_completed 查询失败: {e}")
            return False

    def get_status(self, document_id: str) -> Optional[Dict[str, Any]]:
        """获取文档完整状态记录"""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT * FROM knowledge_ingestion_status WHERE document_id = %s",
                    (document_id,),
                )
                row = cur.fetchone()
                if row and row.get("metadata"):
                    if isinstance(row["metadata"], str):
                        row["metadata"] = json.loads(row["metadata"])
                return row
        except Exception as e:
            logger.warning(f"[IngestionTracker] get_status 查询失败: {e}")
            return None

    def mark_processing(
        self,
        document_id: str,
        filename: str,
        source_type: str,
        filepath: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """标记文档开始处理（UPSERT）"""
        try:
            conn = self._get_conn()
            meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO knowledge_ingestion_status
                        (document_id, filename, filepath, source_type, status, metadata, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'processing', %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE
                        status = 'processing',
                        error_message = NULL,
                        metadata = COALESCE(%s, metadata),
                        updated_at = NOW()
                    """,
                    (document_id, filename, filepath, source_type, meta_json, meta_json),
                )
            return True
        except Exception as e:
            logger.warning(f"[IngestionTracker] mark_processing 失败: {e}")
            return False

    def mark_completed(
        self,
        document_id: str,
        chunk_count: int = 0,
        vector_count: int = 0,
        total_chars: int = 0,
        processing_time_ms: int = 0,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """标记文档处理完成"""
        try:
            conn = self._get_conn()
            meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
            with conn.cursor() as cur:
                if meta_json:
                    cur.execute(
                        """
                        UPDATE knowledge_ingestion_status
                        SET status = 'completed',
                            chunk_count = %s,
                            vector_count = %s,
                            total_chars = %s,
                            processing_time_ms = %s,
                            error_message = NULL,
                            metadata = %s,
                            updated_at = NOW()
                        WHERE document_id = %s
                        """,
                        (chunk_count, vector_count, total_chars, processing_time_ms, meta_json, document_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE knowledge_ingestion_status
                        SET status = 'completed',
                            chunk_count = %s,
                            vector_count = %s,
                            total_chars = %s,
                            processing_time_ms = %s,
                            error_message = NULL,
                            updated_at = NOW()
                        WHERE document_id = %s
                        """,
                        (chunk_count, vector_count, total_chars, processing_time_ms, document_id),
                    )
            return True
        except Exception as e:
            logger.warning(f"[IngestionTracker] mark_completed 失败: {e}")
            return False

    def mark_failed(self, document_id: str, error_message: str = "") -> bool:
        """标记文档处理失败"""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE knowledge_ingestion_status
                    SET status = 'failed',
                        error_message = %s,
                        updated_at = NOW()
                    WHERE document_id = %s
                    """,
                    (error_message[:65535] if error_message else "", document_id),
                )
            return True
        except Exception as e:
            logger.warning(f"[IngestionTracker] mark_failed 失败: {e}")
            return False

    def list_all(
        self,
        source_type: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """列出所有文档状态"""
        try:
            conn = self._get_conn()
            sql = "SELECT * FROM knowledge_ingestion_status WHERE 1=1"
            params: list = []

            if source_type:
                sql += " AND source_type = %s"
                params.append(source_type)
            if status:
                sql += " AND status = %s"
                params.append(status)

            sql += " ORDER BY updated_at DESC LIMIT %s"
            params.append(limit)

            with conn.cursor() as cur:
                cur.execute(sql, params)
                rows = cur.fetchall()
                for row in rows:
                    if row.get("metadata") and isinstance(row["metadata"], str):
                        row["metadata"] = json.loads(row["metadata"])
                return rows
        except Exception as e:
            logger.warning(f"[IngestionTracker] list_all 查询失败: {e}")
            return []

    def get_summary(self) -> Dict[str, Any]:
        """获取摄入状态汇总"""
        try:
            conn = self._get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        source_type,
                        status,
                        COUNT(*) as count,
                        SUM(chunk_count) as total_chunks,
                        SUM(vector_count) as total_vectors,
                        SUM(total_chars) as total_chars
                    FROM knowledge_ingestion_status
                    GROUP BY source_type, status
                    ORDER BY source_type, status
                    """
                )
                rows = cur.fetchall()
                return {
                    "groups": rows,
                    "total_documents": sum(r["count"] for r in rows),
                    "total_vectors": sum(r["total_vectors"] or 0 for r in rows),
                }
        except Exception as e:
            logger.warning(f"[IngestionTracker] get_summary 失败: {e}")
            return {"groups": [], "total_documents": 0, "total_vectors": 0}

    # ─── 回填已有数据 ─────────────────────────────────────

    def backfill_existing(
        self,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
        collection: str = "training_knowledge",
    ) -> Dict[str, int]:
        """
        扫描 Qdrant 已有数据，回填历史记录到 MySQL。
        按 source+filename 聚合，每个文件一条记录。
        """
        _host = qdrant_host or os.getenv("QDRANT_HOST", "qdrant")
        _port = qdrant_port or int(os.getenv("QDRANT_PORT", "6333"))

        try:
            from qdrant_client import QdrantClient
        except ImportError:
            logger.error("qdrant_client 未安装，无法回填")
            return {"error": "qdrant_client not installed"}

        client = QdrantClient(host=_host, port=_port, timeout=30)
        info = client.get_collection(collection)
        total_points = info.points_count
        logger.info(f"[Backfill] Qdrant集合 {collection}: {total_points} points")

        # 滚动读取所有 payload
        file_stats: Dict[str, Dict[str, Any]] = {}
        offset = None
        scanned = 0

        while True:
            results, next_offset = client.scroll(
                collection_name=collection,
                limit=256,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            if not results:
                break

            for point in results:
                payload = point.payload or {}
                source = payload.get("source", "unknown")
                filename = payload.get("filename", "unknown")
                char_count = payload.get("char_count", 0)

                key = f"{source}::{filename}"
                if key not in file_stats:
                    file_stats[key] = {
                        "source": source,
                        "filename": filename,
                        "chunk_count": 0,
                        "total_chars": 0,
                        "metadata_sample": {},
                    }

                file_stats[key]["chunk_count"] += 1
                file_stats[key]["total_chars"] += char_count or 0

                # 保留一些元数据
                if not file_stats[key]["metadata_sample"]:
                    for k in ("title", "category", "bvid", "duration", "chapter", "language"):
                        if k in payload:
                            file_stats[key]["metadata_sample"][k] = payload[k]

            scanned += len(results)
            if next_offset is None:
                break
            offset = next_offset

        logger.info(f"[Backfill] 扫描完成: {scanned} points → {len(file_stats)} 个文件")

        # 写入 MySQL
        inserted = 0
        skipped = 0

        for key, stats in file_stats.items():
            source = stats["source"]
            filename = stats["filename"]

            # 映射 source_type
            if source in ("bilibili_subtitle",):
                source_type = "bilibili_subtitle"
            elif source in ("pdf_textbook",):
                source_type = "pdf_textbook"
            else:
                source_type = "markdown_note"

            doc_id = generate_document_id(f"{source_type}::{filename}")

            if self.is_completed(doc_id):
                skipped += 1
                continue

            self.mark_processing(
                document_id=doc_id,
                filename=filename,
                source_type=source_type,
                filepath=None,
                metadata=stats["metadata_sample"] if stats["metadata_sample"] else None,
            )
            self.mark_completed(
                document_id=doc_id,
                chunk_count=stats["chunk_count"],
                vector_count=stats["chunk_count"],
                total_chars=stats["total_chars"],
                processing_time_ms=0,
            )
            inserted += 1

        logger.info(f"[Backfill] 回填完成: 新增 {inserted}, 跳过 {skipped}")
        return {"inserted": inserted, "skipped": skipped, "total_files": len(file_stats)}


# ─── CLI 入口 ─────────────────────────────────────────────

def main():
    """命令行入口：支持 status / summary / backfill 子命令"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    parser = argparse.ArgumentParser(description="知识摄入状态追踪器")
    sub = parser.add_subparsers(dest="command")

    # status
    p_status = sub.add_parser("status", help="查询文档状态")
    p_status.add_argument("document_id", help="文档ID")

    # summary
    sub.add_parser("summary", help="汇总统计")

    # list
    p_list = sub.add_parser("list", help="列出文档")
    p_list.add_argument("--source-type", choices=["bilibili_subtitle", "pdf_textbook", "markdown_note"])
    p_list.add_argument("--status", choices=["pending", "processing", "completed", "failed"])
    p_list.add_argument("--limit", type=int, default=50)

    # backfill
    sub.add_parser("backfill", help="从Qdrant回填历史记录")

    # test
    sub.add_parser("test", help="运行基本CRUD测试")

    args = parser.parse_args()
    tracker = IngestionTracker()

    try:
        if args.command == "status":
            result = tracker.get_status(args.document_id)
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        elif args.command == "summary":
            result = tracker.get_summary()
            print(json.dumps(result, ensure_ascii=False, indent=2, default=str))

        elif args.command == "list":
            rows = tracker.list_all(
                source_type=args.source_type,
                status=args.status,
                limit=args.limit,
            )
            for r in rows:
                print(f"  [{r['status']:10s}] {r['source_type']:20s} {r['filename']}")
            print(f"\n共 {len(rows)} 条记录")

        elif args.command == "backfill":
            result = tracker.backfill_existing()
            print(json.dumps(result, ensure_ascii=False, indent=2))

        elif args.command == "test":
            _run_crud_test(tracker)

        else:
            parser.print_help()
    finally:
        tracker.close()


def _run_crud_test(tracker: IngestionTracker):
    """基本 CRUD 测试"""
    test_id = generate_document_id("__test__/crud_test.md")
    print(f"测试 document_id: {test_id}")

    # 1. mark_processing
    ok = tracker.mark_processing(test_id, "crud_test.md", "markdown_note", filepath="__test__/crud_test.md")
    print(f"  mark_processing: {'OK' if ok else 'FAIL'}")

    # 2. get_status
    st = tracker.get_status(test_id)
    assert st is not None and st["status"] == "processing", f"期望 processing, 实际 {st}"
    print(f"  get_status(processing): OK")

    # 3. is_completed (should be False)
    assert not tracker.is_completed(test_id)
    print(f"  is_completed(False): OK")

    # 4. mark_completed
    ok = tracker.mark_completed(test_id, chunk_count=10, vector_count=10, total_chars=5000, processing_time_ms=1234)
    print(f"  mark_completed: {'OK' if ok else 'FAIL'}")

    # 5. is_completed (should be True)
    assert tracker.is_completed(test_id)
    print(f"  is_completed(True): OK")

    # 6. mark_failed (覆盖测试)
    ok = tracker.mark_failed(test_id, error_message="测试错误")
    st = tracker.get_status(test_id)
    assert st["status"] == "failed"
    print(f"  mark_failed: OK")

    # 7. 清理测试数据
    try:
        conn = tracker._get_conn()
        with conn.cursor() as cur:
            cur.execute("DELETE FROM knowledge_ingestion_status WHERE document_id = %s", (test_id,))
        print(f"  cleanup: OK")
    except Exception as e:
        print(f"  cleanup: FAIL ({e})")

    print("\n全部 CRUD 测试通过!")


if __name__ == "__main__":
    main()
