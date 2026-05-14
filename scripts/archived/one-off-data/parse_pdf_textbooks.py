#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PDF教材解析与知识提取脚本

纯文本提取方案：使用 pypdf 解析PDF → 章节检测 → 语义Chunk → 输出Markdown/JSON
不依赖 LLM，适合大批量教材的预处理阶段。

版本: v1.0.0
日期: 2026-02-16
作者: 薛小川

使用方式:
    # 解析所有PDF，输出JSON
    python scripts/parse_pdf_textbooks.py --input .books/ --output-format json

    # 解析单个PDF，输出Markdown
    python scripts/parse_pdf_textbooks.py --input .books/AMJ-04-107.pdf --output-format markdown

    # Dry-run模式（只统计，不输出文件）
    python scripts/parse_pdf_textbooks.py --input .books/ --dry-run

    # 自定义chunk参数
    python scripts/parse_pdf_textbooks.py --input .books/ --chunk-size 1000 --chunk-overlap 200
"""

import os
import re
import sys
import json
import logging
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

# ---------------------------------------------------------------------------
# pypdf 依赖检查
# ---------------------------------------------------------------------------
try:
    from pypdf import PdfReader
except ImportError:
    print("=" * 60)
    print("ERROR: pypdf 未安装。请在容器内执行:")
    print("  pip install pypdf")
    print("=" * 60)
    sys.exit(1)

# ---------------------------------------------------------------------------
# 日志配置
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("pdf_parser")

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 已知PDF元数据（手动维护，提升章节检测准确度）
PDF_METADATA: Dict[str, Dict[str, Any]] = {
    "Open-Textbook-of-Exercise-Physiology": {
        "title": "Open Textbook of Exercise Physiology",
        "language": "en",
        "domain": "exercise_physiology",
        "estimated_pages": 317,
    },
    "foundationsoffitnessprogramming": {
        "title": "NSCA Foundations of Fitness Programming",
        "language": "en",
        "domain": "fitness_programming",
        "estimated_pages": 35,
    },
    "Introduction_to_Sports_Biomechanics": {
        "title": "Introduction to Sports Biomechanics",
        "language": "en",
        "domain": "sports_biomechanics",
        "estimated_pages": 315,
    },
    "AMJ-04-107": {
        "title": "AMJ-04-107 Research Paper",
        "language": "en",
        "domain": "research_paper",
        "estimated_pages": 4,
    },
}

# 章节标题检测正则（英文教材常见格式）
CHAPTER_PATTERNS = [
    # "Chapter 1: Title" / "CHAPTER 1 Title"
    re.compile(r"^(?:CHAPTER|Chapter)\s+(\d+)\s*[:\.\-–—]?\s*(.+)", re.MULTILINE),
    # "1. Title" / "1 Title" (行首数字编号，标题较长)
    re.compile(r"^(\d{1,2})\.\s+([A-Z][A-Za-z\s,&\-]{10,})", re.MULTILINE),
    # "PART I" / "Part One"
    re.compile(r"^(?:PART|Part)\s+(\w+)\s*[:\.\-–—]?\s*(.*)", re.MULTILINE),
    # 全大写标题行（至少3个单词）
    re.compile(r"^([A-Z][A-Z\s,&\-]{15,})$", re.MULTILINE),
]

# 节标题检测（二级标题）
SECTION_PATTERNS = [
    # "1.1 Title" / "1.1. Title"
    re.compile(r"^(\d{1,2}\.\d{1,2})\.?\s+([A-Z][A-Za-z\s,&\-]{5,})", re.MULTILINE),
    # 首字母大写的独立短行（可能是小节标题）
    re.compile(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,6})\s*$", re.MULTILINE),
]


# ═══════════════════════════════════════════════════════════════════════════
# 核心类
# ═══════════════════════════════════════════════════════════════════════════


class PDFTextbookParser:
    """PDF教材解析器：提取文本 → 检测章节 → 语义Chunk"""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 180,
        output_dir: str = "data/pdf_chunks",
        output_format: str = "json",
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.output_dir = Path(PROJECT_ROOT) / output_dir
        self.output_format = output_format

        # 检查点
        self.checkpoint_file = Path(PROJECT_ROOT) / "data" / "pdf_parse_checkpoint.json"
        self.checkpoint: Dict[str, Any] = self._load_checkpoint()

        # 统计
        self.stats: Dict[str, Any] = {
            "total_files": 0,
            "processed_files": 0,
            "skipped_files": 0,
            "total_pages": 0,
            "total_chunks": 0,
            "total_chars": 0,
        }

    # ------------------------------------------------------------------
    # 检查点管理
    # ------------------------------------------------------------------

    def _load_checkpoint(self) -> Dict[str, Any]:
        """加载断点续传检查点"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logger.info(f"检查点已加载: {len(data.get('completed', {}))} 个已完成文件")
                return data
            except (json.JSONDecodeError, KeyError):
                logger.warning("检查点文件损坏，重新开始")
        return {"completed": {}, "version": "1.0.0"}

    def _save_checkpoint(self, filename: str, chunk_count: int, page_count: int):
        """保存检查点"""
        self.checkpoint["completed"][filename] = {
            "chunks": chunk_count,
            "pages": page_count,
            "timestamp": datetime.now().isoformat(),
        }
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.checkpoint_file, "w", encoding="utf-8") as f:
            json.dump(self.checkpoint, f, indent=2, ensure_ascii=False)

    def _is_completed(self, filename: str) -> bool:
        """检查文件是否已处理"""
        return filename in self.checkpoint.get("completed", {})

    # ------------------------------------------------------------------
    # PDF文本提取
    # ------------------------------------------------------------------

    def extract_text_from_pdf(self, pdf_path: Path) -> List[Dict[str, Any]]:
        """
        从PDF提取逐页文本

        Returns:
            [{"page": 1, "text": "..."}, ...]
        """
        reader = PdfReader(str(pdf_path))
        pages = []

        for i, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            # 基本清理
            text = self._clean_text(text)
            if text.strip():
                pages.append({"page": i + 1, "text": text})

        logger.info(f"  提取 {len(pages)}/{len(reader.pages)} 页有效文本")
        return pages

    @staticmethod
    def _clean_text(text: str) -> str:
        """清理PDF提取的文本"""
        # 合并断行的单词（连字符换行）
        text = re.sub(r"(\w)-\n(\w)", r"\1\2", text)
        # 合并非段落换行（行尾非句号/冒号的换行）
        text = re.sub(r"(?<![.!?:;\n])\n(?=[a-z])", " ", text)
        # 多个空格合并
        text = re.sub(r"[ \t]+", " ", text)
        # 多个空行合并为两个
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    # ------------------------------------------------------------------
    # 章节检测
    # ------------------------------------------------------------------

    def detect_chapters(
        self, pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        基于文本模式检测章节边界

        Returns:
            [{"title": "Chapter 1: ...", "page_start": 1, "page_end": 15, "text": "..."}, ...]
        """
        chapters: List[Dict[str, Any]] = []
        current_chapter: Optional[Dict[str, Any]] = None

        for page_data in pages:
            page_num = page_data["page"]
            text = page_data["text"]

            # 检测章节标题
            chapter_title = self._detect_chapter_title(text)

            if chapter_title and (
                not current_chapter
                or page_num > current_chapter["page_start"] + 1
            ):
                # 关闭上一章
                if current_chapter:
                    current_chapter["page_end"] = page_num - 1
                    chapters.append(current_chapter)

                # 开始新章节
                current_chapter = {
                    "title": chapter_title,
                    "page_start": page_num,
                    "page_end": page_num,
                    "text": text,
                }
            elif current_chapter:
                current_chapter["text"] += "\n\n" + text
                current_chapter["page_end"] = page_num
            else:
                # 第一章之前的内容（前言/目录等）
                current_chapter = {
                    "title": "Front Matter",
                    "page_start": page_num,
                    "page_end": page_num,
                    "text": text,
                }

        # 关闭最后一章
        if current_chapter:
            chapters.append(current_chapter)

        logger.info(f"  检测到 {len(chapters)} 个章节")
        for ch in chapters:
            logger.info(
                f"    [{ch['page_start']}-{ch['page_end']}] {ch['title'][:60]}"
            )

        return chapters

    @staticmethod
    def _detect_chapter_title(text: str) -> Optional[str]:
        """从页面文本中检测章节标题"""
        # 只检查前500字符（标题通常在页面顶部）
        header = text[:500]

        for pattern in CHAPTER_PATTERNS:
            match = pattern.search(header)
            if match:
                # 返回完整匹配的标题
                title = match.group(0).strip()
                # 清理过长的标题
                if len(title) > 100:
                    title = title[:100] + "..."
                return title

        return None

    # ------------------------------------------------------------------
    # 语义Chunk
    # ------------------------------------------------------------------

    def create_chunks(
        self,
        chapters: List[Dict[str, Any]],
        filename: str,
        title: str,
    ) -> List[Dict[str, Any]]:
        """
        将章节文本分割为语义Chunk

        策略：
        1. 按章节分割为大块
        2. 大块内按段落边界二次分割
        3. 保持 chunk_size 目标，chunk_overlap 重叠
        """
        all_chunks: List[Dict[str, Any]] = []
        chunk_index = 0

        for chapter in chapters:
            chapter_chunks = self._split_chapter(chapter["text"])

            for chunk_text in chapter_chunks:
                if not chunk_text.strip():
                    continue

                chunk = {
                    "chunk_id": f"{Path(filename).stem}_chunk_{chunk_index:04d}",
                    "text": chunk_text.strip(),
                    "metadata": {
                        "source": "pdf_textbook",
                        "filename": filename,
                        "title": title,
                        "chapter": chapter["title"],
                        "page_start": chapter["page_start"],
                        "page_end": chapter["page_end"],
                        "chunk_index": chunk_index,
                        "language": "en",
                        "char_count": len(chunk_text.strip()),
                    },
                }
                all_chunks.append(chunk)
                chunk_index += 1

        # 回填 total_chunks
        for chunk in all_chunks:
            chunk["metadata"]["total_chunks"] = len(all_chunks)

        return all_chunks

    def _split_chapter(self, text: str) -> List[str]:
        """
        将章节文本按段落边界分割为目标大小的chunk

        优先在段落边界（双换行）分割，其次在句子边界分割。
        """
        if len(text) <= self.chunk_size:
            return [text] if text.strip() else []

        chunks: List[str] = []
        # 按段落分割
        paragraphs = re.split(r"\n\n+", text)

        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            # 如果当前chunk加上新段落不超过限制，合并
            if len(current_chunk) + len(para) + 2 <= self.chunk_size:
                current_chunk = (
                    current_chunk + "\n\n" + para if current_chunk else para
                )
            else:
                # 当前chunk已满
                if current_chunk:
                    chunks.append(current_chunk)

                # 如果单个段落超过chunk_size，按句子分割
                if len(para) > self.chunk_size:
                    sub_chunks = self._split_by_sentences(para)
                    chunks.extend(sub_chunks)
                    current_chunk = ""
                else:
                    # 重叠：从上一个chunk末尾取overlap字符
                    if chunks and self.chunk_overlap > 0:
                        overlap_text = chunks[-1][-self.chunk_overlap :]
                        # 找到overlap中第一个句子边界
                        sent_break = re.search(r"[.!?]\s+", overlap_text)
                        if sent_break:
                            overlap_text = overlap_text[sent_break.end() :]
                        current_chunk = overlap_text + "\n\n" + para
                    else:
                        current_chunk = para

        if current_chunk.strip():
            chunks.append(current_chunk)

        return chunks

    def _split_by_sentences(self, text: str) -> List[str]:
        """按句子边界分割超长段落"""
        # 英文句子分割
        sentences = re.split(r"(?<=[.!?])\s+", text)
        chunks: List[str] = []
        current = ""

        for sent in sentences:
            if len(current) + len(sent) + 1 <= self.chunk_size:
                current = current + " " + sent if current else sent
            else:
                if current:
                    chunks.append(current)
                current = sent

        if current.strip():
            chunks.append(current)

        return chunks

    # ------------------------------------------------------------------
    # 输出
    # ------------------------------------------------------------------

    def save_chunks_json(
        self, chunks: List[Dict[str, Any]], filename: str
    ) -> Path:
        """保存为JSON格式"""
        out_dir = self.output_dir / "json"
        out_dir.mkdir(parents=True, exist_ok=True)

        stem = Path(filename).stem
        out_path = out_dir / f"{stem}_chunks.json"

        output = {
            "source_file": filename,
            "total_chunks": len(chunks),
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "generated_at": datetime.now().isoformat(),
            "chunks": chunks,
        }

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)

        logger.info(f"  JSON输出: {out_path}")
        return out_path

    def save_chunks_markdown(
        self, chunks: List[Dict[str, Any]], filename: str
    ) -> Path:
        """保存为Markdown格式（与73个MD知识文件格式一致）"""
        out_dir = self.output_dir / "markdown"
        out_dir.mkdir(parents=True, exist_ok=True)

        stem = Path(filename).stem
        title = chunks[0]["metadata"]["title"] if chunks else stem

        # 按章节分组
        chapters: Dict[str, List[Dict[str, Any]]] = {}
        for chunk in chunks:
            ch = chunk["metadata"]["chapter"]
            chapters.setdefault(ch, []).append(chunk)

        out_path = out_dir / f"{stem}.md"

        lines = [
            f"# {title}",
            "",
            f"> Source: `{filename}`",
            f"> Chunks: {len(chunks)} | Generated: {datetime.now().strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
        ]

        for ch_title, ch_chunks in chapters.items():
            page_range = (
                f"(pp. {ch_chunks[0]['metadata']['page_start']}"
                f"-{ch_chunks[-1]['metadata']['page_end']})"
            )
            lines.append(f"## {ch_title} {page_range}")
            lines.append("")

            for chunk in ch_chunks:
                lines.append(chunk["text"])
                lines.append("")

            lines.append("---")
            lines.append("")

        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        logger.info(f"  Markdown输出: {out_path}")
        return out_path

    # ------------------------------------------------------------------
    # 主流程
    # ------------------------------------------------------------------

    def parse_single_pdf(
        self, pdf_path: Path, dry_run: bool = False
    ) -> Dict[str, Any]:
        """解析单个PDF文件"""
        filename = pdf_path.name

        # 断点续传检查
        if self._is_completed(filename):
            prev = self.checkpoint["completed"][filename]
            logger.info(
                f"跳过已处理文件: {filename} "
                f"({prev['chunks']} chunks, {prev['timestamp']})"
            )
            self.stats["skipped_files"] += 1
            return {"filename": filename, "status": "skipped", **prev}

        logger.info(f"解析PDF: {filename} ({pdf_path.stat().st_size / 1024 / 1024:.1f} MB)")

        # 查找元数据
        meta = self._find_metadata(filename)
        title = meta.get("title", pdf_path.stem)

        # Step 1: 提取文本
        pages = self.extract_text_from_pdf(pdf_path)
        total_chars = sum(len(p["text"]) for p in pages)
        logger.info(f"  总字符数: {total_chars:,}")

        # Step 2: 检测章节
        chapters = self.detect_chapters(pages)

        # Step 3: 创建Chunk
        chunks = self.create_chunks(chapters, filename, title)
        logger.info(
            f"  生成 {len(chunks)} 个chunks "
            f"(目标: {self.chunk_size} chars, 重叠: {self.chunk_overlap})"
        )

        # 统计
        result = {
            "filename": filename,
            "title": title,
            "status": "success",
            "pages": len(pages),
            "chapters": len(chapters),
            "chunks": len(chunks),
            "total_chars": total_chars,
            "avg_chunk_size": (
                sum(len(c["text"]) for c in chunks) // max(len(chunks), 1)
            ),
        }

        if dry_run:
            result["status"] = "dry_run"
            logger.info(f"  [DRY-RUN] 不输出文件")
        else:
            # Step 4: 保存输出
            if self.output_format in ("json", "both"):
                self.save_chunks_json(chunks, filename)
            if self.output_format in ("markdown", "both"):
                self.save_chunks_markdown(chunks, filename)

            # 保存检查点
            self._save_checkpoint(filename, len(chunks), len(pages))

        # 更新全局统计
        self.stats["processed_files"] += 1
        self.stats["total_pages"] += len(pages)
        self.stats["total_chunks"] += len(chunks)
        self.stats["total_chars"] += total_chars

        return result

    def parse_directory(
        self, dir_path: Path, dry_run: bool = False
    ) -> List[Dict[str, Any]]:
        """解析目录下所有PDF"""
        pdf_files = sorted(dir_path.glob("*.pdf"))
        self.stats["total_files"] = len(pdf_files)

        logger.info(f"找到 {len(pdf_files)} 个PDF文件")
        logger.info(f"输出格式: {self.output_format}")
        logger.info(f"Chunk参数: size={self.chunk_size}, overlap={self.chunk_overlap}")
        logger.info("=" * 60)

        results = []
        for i, pdf_file in enumerate(pdf_files, 1):
            logger.info(f"\n[{i}/{len(pdf_files)}] 处理中...")
            result = self.parse_single_pdf(pdf_file, dry_run=dry_run)
            results.append(result)

        # 打印汇总
        self._print_summary(results)
        return results

    def _print_summary(self, results: List[Dict[str, Any]]):
        """打印汇总统计"""
        logger.info("\n" + "=" * 60)
        logger.info("PDF教材解析汇总")
        logger.info("=" * 60)
        logger.info(f"  总文件数:   {self.stats['total_files']}")
        logger.info(f"  已处理:     {self.stats['processed_files']}")
        logger.info(f"  已跳过:     {self.stats['skipped_files']}")
        logger.info(f"  总页数:     {self.stats['total_pages']}")
        logger.info(f"  总Chunk数:  {self.stats['total_chunks']}")
        logger.info(f"  总字符数:   {self.stats['total_chars']:,}")
        logger.info("=" * 60)

        # 逐文件统计
        for r in results:
            status_icon = {
                "success": "OK",
                "skipped": "SKIP",
                "dry_run": "DRY",
            }.get(r["status"], "??")
            logger.info(
                f"  [{status_icon}] {r['filename']}: "
                f"{r.get('chunks', '?')} chunks, "
                f"{r.get('pages', '?')} pages"
            )

    @staticmethod
    def _find_metadata(filename: str) -> Dict[str, Any]:
        """根据文件名查找预定义元数据"""
        stem = Path(filename).stem
        for key, meta in PDF_METADATA.items():
            if key.lower() in stem.lower():
                return meta
        return {"title": stem, "language": "en", "domain": "unknown"}


# ═══════════════════════════════════════════════════════════════════════════
# CLI入口
# ═══════════════════════════════════════════════════════════════════════════


def main():
    parser = argparse.ArgumentParser(
        description="PDF教材解析与知识提取（纯文本方案，不依赖LLM）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 解析所有PDF，输出JSON
  python scripts/parse_pdf_textbooks.py --input .books/ --output-format json

  # 解析单个PDF，输出Markdown
  python scripts/parse_pdf_textbooks.py --input .books/AMJ-04-107.pdf --output-format markdown

  # Dry-run（只统计不输出）
  python scripts/parse_pdf_textbooks.py --input .books/ --dry-run

  # 同时输出JSON和Markdown
  python scripts/parse_pdf_textbooks.py --input .books/ --output-format both
        """,
    )

    parser.add_argument(
        "--input",
        required=True,
        help="PDF文件路径或包含PDF的目录路径",
    )
    parser.add_argument(
        "--output-format",
        choices=["json", "markdown", "both"],
        default="json",
        help="输出格式 (默认: json)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/pdf_chunks",
        help="输出目录 (默认: data/pdf_chunks)",
    )
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
        help="目标Chunk大小（字符数，默认: 1000）",
    )
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=180,
        help="Chunk重叠大小（字符数，默认: 180）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run模式：只统计不输出文件",
    )
    parser.add_argument(
        "--reset-checkpoint",
        action="store_true",
        help="重置检查点，重新处理所有文件",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="详细日志输出",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # 创建解析器
    pdf_parser = PDFTextbookParser(
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        output_dir=args.output_dir,
        output_format=args.output_format,
    )

    # 重置检查点
    if args.reset_checkpoint:
        if pdf_parser.checkpoint_file.exists():
            pdf_parser.checkpoint_file.unlink()
            logger.info("检查点已重置")
        pdf_parser.checkpoint = {"completed": {}, "version": "1.0.0"}

    # 解析
    input_path = Path(args.input)
    if not input_path.exists():
        logger.error(f"输入路径不存在: {input_path}")
        sys.exit(1)

    if input_path.is_file() and input_path.suffix.lower() == ".pdf":
        results = [pdf_parser.parse_single_pdf(input_path, dry_run=args.dry_run)]
    elif input_path.is_dir():
        results = pdf_parser.parse_directory(input_path, dry_run=args.dry_run)
    else:
        logger.error(f"无效输入: {input_path}（需要PDF文件或目录）")
        sys.exit(1)

    # 输出JSON结果到stdout
    summary = {
        "status": "completed",
        "stats": pdf_parser.stats,
        "results": results,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
