# -*- coding: utf-8 -*-
"""
知识提取脚本 — 从字幕/PDF中提取结构化知识文章

两条路线：
  A) 字幕 → LLM提炼 → 结构化知识Markdown
  B) PDF  → pdfplumber提取 → LLM提炼 → 结构化知识Markdown

用法:
    # 字幕提取（全部74个）
    docker exec fitness_daml_rag python scripts/extract_knowledge.py --source subtitles --limit 5

    # PDF提取（指定教材）
    docker exec fitness_daml_rag python scripts/extract_knowledge.py --source pdf --limit 3

    # dry-run 只看提取结果不写文件
    docker exec fitness_daml_rag python scripts/extract_knowledge.py --source subtitles --limit 2 --dry-run

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
import time
from pathlib import Path
from typing import Dict, List, Any, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── 分类映射：字幕category → knowledge_categories slug ──
CATEGORY_MAP = {
    "sports_nutrition": "macronutrients",
    "营养学": "macronutrients",
    "injury_rehab": "rehabilitation",
    "康复": "rehabilitation",
    "functional_anatomy": "exercise-physiology",
    "解剖": "exercise-physiology",
    "periodization": "program-design",
    "周期化": "program-design",
    "training_science": "strength-training",
    "exercise_physiology": "exercise-physiology",
    "sports_biomechanics": "biomechanics",
    "NSCA_CSCS": "strength-training",
    "NSCA": "strength-training",
    "ACSM": "cardio-training",
    "其他": "exercise-physiology",
}

# ── PDF教材 → 分类映射 ──
PDF_CATEGORY_MAP = {
    "foundationsoffitnessprogramming": "program-design",
    "Introduction_to_Sports_Biomechanics": "biomechanics",
    "Open-Textbook-of-Exercise-Physiology": "exercise-physiology",
    "AMJ-04-107": "exercise-physiology",
}

EXTRACTION_PROMPT = """你是一位运动科学专家，负责从原始文本中提取结构化知识文章。

## 输入文本
标题: {title}
分类: {category}
来源: {source}

原始内容:
{content}

## 任务
从上述内容中提取 **1-3个** 独立的知识点，每个知识点输出为一篇结构化文章。

## 输出格式（严格遵循，每篇文章用 ===ARTICLE=== 分隔）

===ARTICLE===
---
title: "知识标题（简洁，15字以内）"
category: "{category_slug}"
difficulty: "beginner/intermediate/advanced"
tags: ["标签1", "标签2", "标签3"]
source_title: "{source_title}"
---

## 摘要

（150字以内，概括核心知识点）

## 核心原则

1. **原则名**: 解释
2. **原则名**: 解释

## 适用人群

| 人群 | 适用性 | 注意事项 |
|------|--------|---------|
| 初学者 | ✅/⚠️/❌ | 说明 |
| 中级训练者 | ✅/⚠️/❌ | 说明 |
| 高级训练者 | ✅/⚠️/❌ | 说明 |

## 具体参数

| 参数 | 推荐值 | 范围 | 说明 |
|------|--------|------|------|

## 禁忌症与注意事项

- ⚠️/❌ 注意事项

## 实践建议

1. 建议1
2. 建议2
3. 建议3

===END===

## 规则
- 去除口语化表达（"呃"、"嗯"、"就是说"），提炼专业知识
- 如果原文信息不足以填充某个章节，可以基于运动科学常识补充
- 每篇文章必须有实用价值，不要提取过于琐碎的内容
- tags 使用中文
- 如果原文内容太少或无实质知识，只输出1篇即可
"""


def call_llm(prompt: str, max_tokens: int = 4000) -> str:
    """调用 LLM 提取知识 — 支持多后端，优先免费模型

    优先级: 硅基流动(免费) → 智谱GLM(免费) → DeepSeek(极低价)
    通过环境变量 EXTRACT_LLM_BACKEND 切换: siliconflow / glm / deepseek
    """
    import httpx

    backend = os.getenv("EXTRACT_LLM_BACKEND", "siliconflow")

    if backend == "siliconflow":
        api_key = os.getenv("SILICONFLOW_API_KEY", "sk-howbnsmlmtjmhhermipfqmkfaaobqwjktrrgaafdvejqispb")
        base_url = "https://api.siliconflow.cn/v1"
        model = os.getenv("SILICONFLOW_MODEL", "Qwen/Qwen3-8B")
    elif backend == "glm":
        api_key = os.getenv("GLM_API_KEY", "")
        base_url = "https://open.bigmodel.cn/api/paas/v4"
        model = "glm-4.7-flash"
    else:  # deepseek
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        base_url = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
        model = "deepseek-chat"

    resp = httpx.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.3,
        },
        timeout=120,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def parse_llm_output(output: str) -> List[Dict[str, Any]]:
    """解析 LLM 输出，拆分为多篇文章"""
    articles = []

    # 尝试按 ===ARTICLE=== 分割
    if "===ARTICLE===" in output:
        parts = re.split(r"===ARTICLE===", output)
    else:
        # 兜底：整个输出当作一篇文章
        parts = [output]

    for part in parts:
        part = part.strip()
        if not part or part == "===END===":
            continue
        # 去掉尾部的 ===END===
        part = re.sub(r"===END===\s*$", "", part).strip()
        if not part:
            continue

        # 解析 YAML front matter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", part, re.DOTALL)
        if fm_match:
            try:
                meta = yaml.safe_load(fm_match.group(1))
                content = fm_match.group(2).strip()
                articles.append({"meta": meta, "content": content})
            except yaml.YAMLError as e:
                logger.warning(f"⚠️ YAML解析失败: {e}")
        else:
            # 再尝试：找 --- 开头的块
            fm_blocks = re.findall(r"(---\s*\n.*?\n---\s*\n.*?)(?=\n---\s*\n|\Z)", part, re.DOTALL)
            for block in fm_blocks:
                fm_match2 = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", block.strip(), re.DOTALL)
                if fm_match2:
                    try:
                        meta = yaml.safe_load(fm_match2.group(1))
                        content = fm_match2.group(2).strip()
                        articles.append({"meta": meta, "content": content})
                    except yaml.YAMLError:
                        pass

            if not fm_blocks:
                logger.warning(f"⚠️ 无法解析文章格式，跳过 (前100字: {part[:100]}...)")

    return articles


def save_article(article: Dict[str, Any], output_dir: str, index: int) -> str:
    """保存文章为 Markdown 文件"""
    meta = article["meta"]
    category = meta.get("category", "exercise-physiology")
    title_slug = re.sub(r"[^\w\u4e00-\u9fff]", "-", meta.get("title", f"article-{index}"))
    title_slug = re.sub(r"-+", "-", title_slug).strip("-")[:50]

    cat_dir = os.path.join(output_dir, category)
    os.makedirs(cat_dir, exist_ok=True)

    # 找到下一个可用编号
    existing = [f for f in os.listdir(cat_dir) if f.endswith(".md")]
    next_num = len(existing) + 1
    # 跳过已有编号（如手动创建的01-xxx.md）
    while any(f.startswith(f"{next_num:02d}-") for f in existing):
        next_num += 1

    filename = f"{next_num:02d}-{title_slug}.md"
    filepath = os.path.join(cat_dir, filename)

    # 构建完整 Markdown
    yaml_str = yaml.dump(meta, allow_unicode=True, default_flow_style=False).strip()
    full_content = f"---\n{yaml_str}\nstatus: published\n---\n\n{article['content']}"

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(full_content)

    return filepath


# ── 路线A：字幕提取 ──

def extract_from_subtitles(subtitle_dir: str, output_dir: str, limit: int = 0, dry_run: bool = False) -> int:
    """从字幕文件中提取知识文章"""
    files = sorted([f for f in os.listdir(subtitle_dir) if f.endswith(".md")])
    if limit > 0:
        files = files[:limit]

    # 断点续跑：读取已处理文件记录
    progress_file = os.path.join(output_dir, ".progress_subtitles.json")
    processed = set()
    if os.path.exists(progress_file):
        with open(progress_file, "r") as pf:
            processed = set(json.load(pf))
        logger.info(f"📋 已处理 {len(processed)} 个文件，跳过")

    logger.info(f"📺 字幕提取: {len(files)} 个文件 (待处理: {len(files) - len(processed)})")
    total_articles = 0

    for i, fname in enumerate(files):
        if fname in processed:
            logger.info(f"[{i+1}/{len(files)}] ⏭️ 跳过已处理: {fname}")
            continue

        filepath = os.path.join(subtitle_dir, fname)
        logger.info(f"\n[{i+1}/{len(files)}] 📄 {fname}")

        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

        # 解析 YAML front matter
        fm_match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
        if not fm_match:
            logger.warning(f"  ⚠️ 无 YAML，跳过")
            continue

        try:
            meta = yaml.safe_load(fm_match.group(1))
        except yaml.YAMLError:
            logger.warning(f"  ⚠️ YAML解析失败，跳过")
            continue

        content = fm_match.group(2).strip()
        title = meta.get("title", fname)
        category = meta.get("category", "其他")
        category_slug = CATEGORY_MAP.get(category, "exercise-physiology")

        # 截断过长内容（DeepSeek 输入限制）
        if len(content) > 12000:
            content = content[:12000] + "\n\n[...内容截断...]"

        prompt = EXTRACTION_PROMPT.format(
            title=title,
            category=category,
            source=f"B站视频字幕: {meta.get('bvid', '')}",
            content=content,
            category_slug=category_slug,
            source_title=title,
        )

        try:
            logger.info(f"  🤖 调用 Claude 提取...")
            result = call_llm(prompt)
            logger.debug(f"  📝 LLM原始输出前200字: {result[:200]}")
            articles = parse_llm_output(result)
            logger.info(f"  ✅ 提取到 {len(articles)} 篇文章")

            if dry_run:
                for a in articles:
                    logger.info(f"    [DRY-RUN] {a['meta'].get('title', '?')}")
            else:
                for idx, article in enumerate(articles):
                    # 补充来源信息
                    article["meta"]["source_title"] = title
                    article["meta"]["source_bvid"] = meta.get("bvid", "")
                    article["meta"]["source_type"] = "bilibili_subtitle"
                    fp = save_article(article, output_dir, total_articles + idx)
                    logger.info(f"    💾 {fp}")

            total_articles += len(articles)
            time.sleep(0.5)  # Kiro反代限速

            # 记录已处理文件
            if not dry_run:
                processed.add(fname)
                with open(progress_file, "w") as pf:
                    json.dump(list(processed), pf)

        except Exception as e:
            logger.error(f"  ❌ 提取失败: {e}")
            continue

    return total_articles


# ── 路线B：PDF提取 ──

def extract_text_from_pdf(pdf_path: str) -> List[Dict[str, str]]:
    """用 pdfplumber 提取 PDF 文本，按页分组"""
    import pdfplumber

    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text()
            if text and len(text.strip()) > 50:
                pages.append({"page": i + 1, "text": text.strip()})

    return pages


def chunk_pages(pages: List[Dict[str, str]], chunk_size: int = 8000) -> List[Dict[str, Any]]:
    """将页面合并为适合 LLM 处理的 chunk"""
    chunks = []
    current_text = ""
    current_pages = []

    for page in pages:
        if len(current_text) + len(page["text"]) > chunk_size and current_text:
            chunks.append({
                "text": current_text,
                "pages": f"{current_pages[0]}-{current_pages[-1]}",
            })
            current_text = ""
            current_pages = []

        current_text += page["text"] + "\n\n"
        current_pages.append(page["page"])

    if current_text:
        chunks.append({
            "text": current_text,
            "pages": f"{current_pages[0]}-{current_pages[-1]}",
        })

    return chunks


def extract_from_pdfs(books_dir: str, output_dir: str, limit: int = 0, dry_run: bool = False) -> int:
    """从 PDF 教材中提取知识文章"""
    pdf_files = sorted([f for f in os.listdir(books_dir) if f.endswith(".pdf")])
    logger.info(f"📚 PDF提取: {len(pdf_files)} 本教材")

    # 断点续跑：记录已处理的 pdf_name:chunk_pages
    progress_file = os.path.join(output_dir, ".progress_pdf.json")
    processed = set()
    if os.path.exists(progress_file):
        with open(progress_file, "r") as pf:
            processed = set(json.load(pf))
        logger.info(f"📋 已处理 {len(processed)} 个 chunk，跳过")

    total_articles = 0

    for pdf_name in pdf_files:
        pdf_path = os.path.join(books_dir, pdf_name)
        stem = Path(pdf_name).stem
        category_slug = PDF_CATEGORY_MAP.get(stem, "exercise-physiology")

        logger.info(f"\n📖 {pdf_name} → {category_slug}")

        # 提取文本
        pages = extract_text_from_pdf(pdf_path)
        logger.info(f"  📄 提取到 {len(pages)} 页有效文本")

        if not pages:
            logger.warning(f"  ⚠️ 无有效文本，跳过")
            continue

        # 分 chunk
        chunks = chunk_pages(pages)
        logger.info(f"  📦 分为 {len(chunks)} 个 chunk")

        if limit > 0:
            chunks = chunks[:limit]

        for i, chunk in enumerate(chunks):
            chunk_key = f"{pdf_name}:{chunk['pages']}"
            if chunk_key in processed:
                logger.info(f"  [{i+1}/{len(chunks)}] ⏭️ 跳过已处理: pages {chunk['pages']}")
                continue

            logger.info(f"  [{i+1}/{len(chunks)}] pages {chunk['pages']}")

            prompt = EXTRACTION_PROMPT.format(
                title=f"{stem} (pages {chunk['pages']})",
                category=category_slug,
                source=f"教材: {pdf_name}",
                content=chunk["text"][:12000],
                category_slug=category_slug,
                source_title=pdf_name,
            )

            try:
                logger.info(f"    🤖 调用 Claude 提取...")
                result = call_llm(prompt)
                articles = parse_llm_output(result)
                logger.info(f"    ✅ 提取到 {len(articles)} 篇文章")

                if dry_run:
                    for a in articles:
                        logger.info(f"      [DRY-RUN] {a['meta'].get('title', '?')}")
                else:
                    for idx, article in enumerate(articles):
                        article["meta"]["source_title"] = pdf_name
                        article["meta"]["source_pages"] = chunk["pages"]
                        article["meta"]["source_type"] = "pdf_textbook"
                        fp = save_article(article, output_dir, total_articles + idx)
                        logger.info(f"      💾 {fp}")

                total_articles += len(articles)
                time.sleep(0.5)

                # 记录已处理 chunk
                if not dry_run:
                    processed.add(chunk_key)
                    with open(progress_file, "w") as pf:
                        json.dump(list(processed), pf)

            except Exception as e:
                logger.error(f"    ❌ 提取失败: {e}")
                continue

    return total_articles


def main():
    parser = argparse.ArgumentParser(description="知识提取: 字幕/PDF → 结构化知识文章")
    parser.add_argument("--source", choices=["subtitles", "pdf", "all"], default="all", help="提取来源")
    parser.add_argument("--subtitle-dir", default="/app/knowledge_texts", help="字幕目录")
    parser.add_argument("--books-dir", default="/app/.books", help="PDF教材目录")
    parser.add_argument("--output-dir", default="scripts/knowledge_output", help="输出目录")
    parser.add_argument("--limit", type=int, default=0, help="每个来源最多处理N个文件/chunk（0=全部）")
    parser.add_argument("--dry-run", action="store_true", help="仅提取不写文件")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    total = 0

    if args.source in ("subtitles", "all"):
        n = extract_from_subtitles(args.subtitle_dir, args.output_dir, args.limit, args.dry_run)
        total += n
        logger.info(f"\n📺 字幕提取完成: {n} 篇文章")

    if args.source in ("pdf", "all"):
        n = extract_from_pdfs(args.books_dir, args.output_dir, args.limit, args.dry_run)
        total += n
        logger.info(f"\n📚 PDF提取完成: {n} 篇文章")

    logger.info(f"\n{'='*60}")
    logger.info(f"📊 总计提取: {total} 篇知识文章 → {args.output_dir}/")
    logger.info(f"下一步: python scripts/import_knowledge.py --dir {args.output_dir}")


if __name__ == "__main__":
    main()
