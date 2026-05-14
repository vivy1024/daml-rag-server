"""知识 chunk 工具函数"""

from typing import List, Dict


def make_chunk(
    category: str,
    subcategory: str,
    title: str,
    content: str,
    keywords: List[str] = None,
    related_muscles: List[str] = None,
    related_injuries: List[str] = None,
) -> Dict:
    return {
        "source": "ai_knowledge_base",
        "category": category,
        "subcategory": subcategory,
        "title": title,
        "content": content,
        "keywords": keywords or [],
        "confidence": "high",
        "citation_note": "基于运动科学共识，AI 整理生成",
        "language": "zh",
        "related_muscles": related_muscles or [],
        "related_injuries": related_injuries or [],
    }
