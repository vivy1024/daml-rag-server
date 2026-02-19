# -*- coding: utf-8 -*-
"""
VisionMessageBuilder - 多模态消息构建器

构建 OpenAI 兼容格式的 multimodal messages，
支持食物识别专用 prompt 和通用图片分析。

版本: v1.0.0
日期: 2026-02-20
"""

import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# 食物相关关键词（用于检测图片上下文）
_FOOD_KEYWORDS = re.compile(
    r"吃|热量|卡路里|营养|午餐|晚餐|早餐|食物|饮食|"
    r"蛋白质|碳水|脂肪|减脂餐|增肌餐|食谱|"
    r"meal|food|calorie|protein|carb|fat|diet",
    re.IGNORECASE,
)

FOOD_RECOGNITION_PROMPT = """## 食物识别任务

请分析照片中的食物，对每种食物提供：
1. 食物名称（中文）
2. 估算重量（克）
3. 热量（千卡）
4. 蛋白质（克）
5. 碳水化合物（克）
6. 脂肪（克）

输出格式：
| 食物 | 重量 | 热量 | 蛋白质 | 碳水 | 脂肪 |
|------|------|------|--------|------|------|

最后给出总计和简要营养评价。

> ⚠️ 以上为AI估算值，仅供参考，实际营养成分可能有差异。"""


class VisionMessageBuilder:
    """构建 multimodal LLM 消息（OpenAI 兼容格式）"""

    def build_messages(
        self,
        query: str,
        attachments: List[Dict[str, Any]],
        system_prompt: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
    ) -> List[Dict[str, Any]]:
        """
        构建 OpenAI 兼容格式的 multimodal messages。

        Args:
            query: 用户查询文本
            attachments: 附件列表，每项含 data(base64), mime_type
            system_prompt: 系统提示词
            conversation_history: 对话历史

        Returns:
            OpenAI messages 格式列表
        """
        messages = [{"role": "system", "content": system_prompt}]

        # 添加对话历史
        if conversation_history:
            for h in conversation_history:
                messages.append({
                    "role": h.get("role", "user"),
                    "content": h.get("content", ""),
                })

        # 检测图片上下文，注入专用 prompt
        context = self.detect_image_context(query)
        if context == "food_recognition":
            query = f"{query}\n\n{FOOD_RECOGNITION_PROMPT}"

        # 构建 multimodal user message
        content_parts: List[Dict[str, Any]] = [
            {"type": "text", "text": query}
        ]

        image_attachments = [
            a for a in attachments
            if a.get("mime_type", "").startswith("image/")
        ]

        for att in image_attachments:
            base64_data = att.get("data", "")
            mime_type = att.get("mime_type", "image/jpeg")
            content_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{mime_type};base64,{base64_data}"
                }
            })

        messages.append({"role": "user", "content": content_parts})

        logger.info(
            f"Vision消息构建: context={context}, "
            f"images={len(image_attachments)}, "
            f"history={len(conversation_history or [])}"
        )
        return messages

    def detect_image_context(self, query: str) -> str:
        """
        检测图片上下文场景。

        Returns:
            "food_recognition" 或 "general"
        """
        if _FOOD_KEYWORDS.search(query):
            return "food_recognition"
        return "general"
