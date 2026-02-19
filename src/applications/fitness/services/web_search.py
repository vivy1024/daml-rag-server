# -*- coding: utf-8 -*-
"""
WebSearch 兜底检索服务

Layer4: 当 L1-L3 检索结果为空或低置信度时，
使用 DuckDuckGo 免费搜索作为兜底。

触发条件：
1. 三层检索结果为空
2. 查询含时效性关键词（最新、2026、新研究等）
3. 用户明确要求搜索（搜一下、查一查等）

版本: v1.0.0
日期: 2026-02-20
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# 时效性关键词
_TEMPORAL_KEYWORDS = re.compile(
    r"最新|2026|2025|新研究|最近|刚出的|新发现|最新版",
)

# 用户主动搜索关键词
_SEARCH_KEYWORDS = re.compile(
    r"搜一下|搜索|网上|查一查|有没有最新|帮我查|上网",
)


def should_web_search(query: str, retrieval_results: Optional[Dict] = None) -> bool:
    """
    判断是否需要触发网络搜索。

    Args:
        query: 用户查询
        retrieval_results: 三层检索结果（可选）

    Returns:
        是否触发 WebSearch
    """
    # 条件1: 检索结果为空
    if retrieval_results:
        results = retrieval_results.get("results", [])
        if not results:
            return True

    # 条件2: 时效性关键词
    if _TEMPORAL_KEYWORDS.search(query):
        return True

    # 条件3: 用户主动搜索
    if _SEARCH_KEYWORDS.search(query):
        return True

    return False


async def web_search_fallback(query: str, max_results: int = 3, timeout: float = 5.0) -> List[Dict[str, str]]:
    """
    Layer4: WebSearch 兜底，DuckDuckGo（完全免费，无需 API Key）。

    Args:
        query: 搜索查询
        max_results: 最大结果数
        timeout: 超时秒数

    Returns:
        搜索结果列表 [{"title": ..., "url": ..., "snippet": ...}]
    """
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS

        def _search():
            with DDGS() as ddgs:
                results = list(ddgs.text(query, region="cn-zh", max_results=max_results))
                return [
                    {
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", "")[:300],
                    }
                    for r in results
                ]

        results = await asyncio.wait_for(
            asyncio.to_thread(_search),
            timeout=timeout,
        )
        if results:
            logger.info(f"🔍 WebSearch 返回 {len(results)} 条结果: query={query[:30]}...")
        return results

    except asyncio.TimeoutError:
        logger.warning(f"⏰ WebSearch 超时 ({timeout}s): {query[:30]}...")
        return []
    except ImportError:
        logger.debug("duckduckgo-search 未安装，WebSearch 跳过")
        return []
    except Exception as e:
        logger.warning(f"🔍 WebSearch 失败: {e}")
        return []


def format_web_results_for_prompt(web_results: List[Dict[str, str]]) -> str:
    """
    格式化搜索结果为 Prompt 注入段落。

    Returns:
        格式化的 markdown 文本，或空字符串
    """
    if not web_results:
        return ""

    lines = ["\n## 📎 网络搜索参考\n"]
    for r in web_results:
        title = r.get("title", "未知")
        url = r.get("url", "")
        snippet = r.get("snippet", "")[:200]
        lines.append(f"- [{title}]({url}): {snippet}")
    lines.append("\n> 请基于以上网络搜索结果回答，并标注来源。\n")
    return "\n".join(lines)
