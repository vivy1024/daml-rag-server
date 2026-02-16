"""
引用溯源追踪器
将检索结果格式化为引用信息，支持前端展示和LLM综合
"""
from typing import List, Dict, Any, Set


class CitationTracker:
    """引用溯源追踪器"""

    def __init__(self):
        """初始化"""
        pass

    def format_citations(self, search_results: List[Dict]) -> List[Dict]:
        """
        将检索结果格式化为引用信息

        Args:
            search_results: 检索结果列表，每个结果包含payload和score

        Returns:
            格式化的引用信息列表
        """
        citations = []

        for i, result in enumerate(search_results):
            # 兼容不同的结果格式
            if 'payload' in result:
                payload = result['payload']
                score = result.get('score', 0)
            else:
                payload = result
                score = result.get('score', 0)

            # 提取关键信息
            citation = {
                "citation_id": i + 1,
                "source_file": payload.get('source', '未知'),
                "source_type": payload.get('source_type', '未知'),
                "doc_title": payload.get('doc_title', '未知文档'),
                "section_path": payload.get('section_path', ''),
                "content_type": payload.get('content_type', ''),
                "relevance_score": round(score, 4),
                "text_preview": self._get_text_preview(payload),
                "chunk_index": payload.get('chunk_index', 0),
                "total_chunks": payload.get('total_chunks', 1),
                "position_label": payload.get('position_label', ''),
                "position_ratio": payload.get('position_ratio', 0),
            }

            # 添加特定来源的额外信息
            if payload.get('source') == 'bilibili_subtitle':
                citation['bvid'] = payload.get('bvid', '')
                citation['timestamp_start'] = payload.get('timestamp_start', 0)
                citation['timestamp_end'] = payload.get('timestamp_end', 0)
                citation['video_title'] = payload.get('title', payload.get('doc_title', ''))

            citations.append(citation)

        return citations

    def _get_text_preview(self, payload: Dict, max_length: int = 200) -> str:
        """获取文本预览"""
        text = payload.get('chunk_text', payload.get('text', ''))
        if len(text) > max_length:
            return text[:max_length] + '...'
        return text

    def format_for_llm(self, citations: List[Dict]) -> str:
        """
        格式化引用信息供LLM综合阶段使用

        Args:
            citations: 引用信息列表

        Returns:
            格式化的引用文本，包含[1] [2] [3]标记
        """
        if not citations:
            return ""

        lines = ["## 参考资料\n"]

        for citation in citations:
            citation_id = citation['citation_id']
            doc_title = citation['doc_title']
            section = citation['section_path']
            position = citation['position_label']
            source_type = citation['source_type']

            # 构建引用标记
            citation_mark = f"[{citation_id}]"

            # 构建来源描述
            source_desc = f"{doc_title}"
            if section:
                source_desc += f" - {section}"
            if position:
                source_desc += f"（{position}）"

            # 添加来源类型标识
            type_emoji = {
                'video': '🎥',
                'pdf': '📄',
                'markdown': '📝',
                'text': '📃',
            }.get(source_type, '📚')

            lines.append(f"{citation_mark} {type_emoji} {source_desc}")

            # 对于视频，添加时间戳
            if citation.get('bvid'):
                timestamp = citation.get('timestamp_start', 0)
                minutes = timestamp // 60
                seconds = timestamp % 60
                lines.append(f"   时间: {minutes:02d}:{seconds:02d}")

            lines.append("")

        lines.append("\n💡 提示：在回答中使用 [1] [2] 等标记引用上述资料\n")

        return "\n".join(lines)

    def format_for_frontend(self, citations: List[Dict]) -> Dict[str, Any]:
        """
        格式化引用信息供前端展示

        Args:
            citations: 引用信息列表

        Returns:
            前端友好的JSON结构
        """
        if not citations:
            return {
                "citations": [],
                "total_sources": 0,
                "source_types": {},
                "content_types": {},
            }

        # 统计来源类型
        source_types: Dict[str, int] = {}
        content_types: Dict[str, int] = {}
        unique_sources: Set[str] = set()

        for citation in citations:
            source_type = citation['source_type']
            content_type = citation['content_type']
            source_file = citation['source_file']

            source_types[source_type] = source_types.get(source_type, 0) + 1
            if content_type:
                content_types[content_type] = content_types.get(content_type, 0) + 1
            unique_sources.add(source_file)

        # 按来源分组
        grouped_citations = self._group_by_source(citations)

        return {
            "citations": citations,
            "grouped_citations": grouped_citations,
            "total_sources": len(unique_sources),
            "total_citations": len(citations),
            "source_types": source_types,
            "content_types": content_types,
            "avg_relevance": round(
                sum(c['relevance_score'] for c in citations) / len(citations), 4
            ) if citations else 0,
        }

    def _group_by_source(self, citations: List[Dict]) -> Dict[str, List[Dict]]:
        """按来源文档分组引用"""
        grouped: Dict[str, List[Dict]] = {}

        for citation in citations:
            doc_title = citation['doc_title']
            if doc_title not in grouped:
                grouped[doc_title] = []
            grouped[doc_title].append(citation)

        return grouped

    def generate_citation_summary(self, citations: List[Dict]) -> str:
        """
        生成引用摘要（用于日志或调试）

        Args:
            citations: 引用信息列表

        Returns:
            引用摘要文本
        """
        if not citations:
            return "无引用"

        summary_lines = [f"共 {len(citations)} 条引用："]

        # 按文档分组统计
        doc_counts: Dict[str, int] = {}
        for citation in citations:
            doc_title = citation['doc_title']
            doc_counts[doc_title] = doc_counts.get(doc_title, 0) + 1

        for doc_title, count in sorted(doc_counts.items(), key=lambda x: x[1], reverse=True):
            summary_lines.append(f"  - {doc_title}: {count}条")

        return "\n".join(summary_lines)

    def extract_citation_ids_from_text(self, text: str) -> List[int]:
        """
        从LLM生成的文本中提取引用ID

        Args:
            text: LLM生成的文本

        Returns:
            引用ID列表
        """
        import re
        # 匹配 [1] [2] [3] 等格式
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, text)
        return [int(m) for m in matches]

    def validate_citations(self, text: str, citations: List[Dict]) -> Dict[str, Any]:
        """
        验证LLM生成的文本中的引用是否有效

        Args:
            text: LLM生成的文本
            citations: 可用的引用列表

        Returns:
            验证结果
        """
        used_ids = self.extract_citation_ids_from_text(text)
        valid_ids = {c['citation_id'] for c in citations}

        invalid_ids = [id for id in used_ids if id not in valid_ids]

        return {
            "total_citations": len(citations),
            "used_citations": len(set(used_ids)),
            "invalid_citations": invalid_ids,
            "is_valid": len(invalid_ids) == 0,
        }


# 便捷函数
def format_search_results_as_citations(search_results: List[Dict]) -> Dict[str, Any]:
    """
    便捷函数：将检索结果格式化为完整的引用信息

    Args:
        search_results: 检索结果列表

    Returns:
        包含多种格式的引用信息
    """
    tracker = CitationTracker()
    citations = tracker.format_citations(search_results)

    return {
        "citations": citations,
        "llm_format": tracker.format_for_llm(citations),
        "frontend_format": tracker.format_for_frontend(citations),
        "summary": tracker.generate_citation_summary(citations),
    }
