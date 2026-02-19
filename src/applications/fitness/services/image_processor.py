# -*- coding: utf-8 -*-
"""
图片处理器

处理用户上传的图片：格式验证、大小检查、压缩、base64编解码。
输出 OpenAI 兼容的 image_url 格式，所有 Vision 模型统一使用。

版本: v1.0.0
日期: 2026-02-20
"""

import base64
import io
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ImageProcessor:
    """图片处理器"""
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_TYPES = {"image/jpeg", "image/png", "image/webp"}
    MAX_DIMENSION = 1024

    def validate(self, attachment: dict) -> bool:
        """验证图片格式和大小"""
        mime_type = attachment.get("mime_type", "")
        if mime_type not in self.ALLOWED_TYPES:
            logger.warning(f"不支持的图片类型: {mime_type}")
            return False

        size = attachment.get("size", 0)
        if size > self.MAX_SIZE:
            logger.warning(f"图片大小超限: {size} > {self.MAX_SIZE}")
            return False

        data = attachment.get("data", "")
        if not data:
            logger.warning("图片数据为空")
            return False

        return True

    def process(self, attachment: dict) -> Optional[dict]:
        """处理图片：验证 → 压缩 → 返回处理结果"""
        if not self.validate(attachment):
            return None

        mime_type = attachment.get("mime_type", "image/jpeg")
        base64_data = attachment.get("data", "")

        # 尝试压缩（需要 Pillow）
        try:
            compressed = self._compress(base64_data, mime_type)
            if compressed:
                base64_data = compressed
        except Exception as e:
            logger.warning(f"图片压缩失败，使用原图: {e}")

        return {
            "base64_data": base64_data,
            "mime_type": mime_type,
            "openai_format": self.to_openai_format(base64_data, mime_type),
        }

    def to_openai_format(self, base64_data: str, mime_type: str) -> dict:
        """转换为 OpenAI 兼容 vision API 格式（所有模型统一使用）"""
        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime_type};base64,{base64_data}"
            }
        }

    def _compress(self, base64_data: str, mime_type: str) -> Optional[str]:
        """服务端图片压缩（最大 1024px）"""
        try:
            from PIL import Image

            img_bytes = base64.b64decode(base64_data)
            img = Image.open(io.BytesIO(img_bytes))

            width, height = img.size
            if width <= self.MAX_DIMENSION and height <= self.MAX_DIMENSION:
                return None  # 无需压缩

            ratio = min(self.MAX_DIMENSION / width, self.MAX_DIMENSION / height)
            new_size = (int(width * ratio), int(height * ratio))
            img = img.resize(new_size, Image.LANCZOS)

            # 输出为 JPEG
            buffer = io.BytesIO()
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)

            compressed_b64 = base64.b64encode(buffer.read()).decode("utf-8")
            logger.info(f"图片压缩: {width}x{height} → {new_size[0]}x{new_size[1]}")
            return compressed_b64

        except ImportError:
            logger.warning("Pillow 未安装，跳过服务端压缩")
            return None
