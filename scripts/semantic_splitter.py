#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
语义分割器模块 - 基于Embedding余弦相似度检测语义断点

替换原有的固定大小分割（800字符/1000字符），使用GTE-Large-zh模型
计算相邻句子的embedding相似度，在语义断点处切分。

核心算法（参考LlamaIndex SemanticSplitter）：
1. 将文本按句子分割（中文句号、问号、感叹号、换行）
2. 用GTE-Large-zh对每个句子编码
3. 计算相邻句子的embedding余弦相似度
4. 相似度低于阈值的位置 = 语义断点
5. 在断点处切分，形成语义chunk
6. 合并过短的chunk（< min_chunk_size），拆分过长的chunk（> max_chunk_size）

版本: v1.0.0
日期: 2026-02-16
作者: 薛小川
"""

import re
import logging
import numpy as np
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# 句子分割正则：中文句号/问号/感叹号/英文句号/换行
# 使用正向后行断言保留分隔符
SENTENCE_SPLIT_PATTERN = re.compile(
    r'(?<=[。！？!?\n])'
    r'|'
    r'(?<=[.]\s)'  # 英文句号后跟空格
)

# 备用：按换行+空行分割（用于拆分过长chunk）
PARAGRAPH_SPLIT_PATTERN = re.compile(r'\n\n+')


class SemanticSplitter:
    """
    基于Embedding余弦相似度的语义分割器

    使用sentence-transformers加载GTE-Large-zh模型，
    计算相邻句子间的语义相似度，在低相似度处切分。
    """

    def __init__(
        self,
        model_name: str = "thenlper/gte-large-zh",
        similarity_threshold: float = 0.5,
        max_chunk_size: int = 1500,
        min_chunk_size: int = 100,
        batch_size: int = 64,
    ):
        """
        Args:
            model_name: sentence-transformers模型名
            similarity_threshold: 语义断点阈值，低于此值视为断点
            max_chunk_size: chunk最大字符数，超过则强制拆分
            min_chunk_size: chunk最小字符数，低于则合并到相邻chunk
            batch_size: embedding批处理大小
        """
        self.model_name = model_name
        self.similarity_threshold = similarity_threshold
        self.max_chunk_size = max_chunk_size
        self.min_chunk_size = min_chunk_size
        self.batch_size = batch_size
        self._model = None

    @property
    def model(self):
        """延迟加载模型"""
        if self._model is None:
            logger.info(f"加载Embedding模型: {self.model_name}")
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            logger.info(f"模型加载完成，设备: {self._model.device}")
        return self._model

    def _split_sentences(self, text: str) -> List[str]:
        """
        将文本分割为句子列表

        支持中英文混合文本，按句号/问号/感叹号/换行分割。
        过短的片段（<10字符）合并到前一个句子。
        """
        # 先按正则分割
        raw_parts = SENTENCE_SPLIT_PATTERN.split(text)
        # 过滤空白
        raw_parts = [p.strip() for p in raw_parts if p.strip()]

        if not raw_parts:
            return [text.strip()] if text.strip() else []

        # 合并过短的片段到前一个句子
        sentences = []
        for part in raw_parts:
            if sentences and len(part) < 10:
                sentences[-1] += part
            else:
                sentences.append(part)

        return sentences

    def _encode_sentences(self, sentences: List[str]) -> np.ndarray:
        """批量编码句子为embedding向量"""
        if not sentences:
            return np.array([])

        all_embeddings = []
        for i in range(0, len(sentences), self.batch_size):
            batch = sentences[i:i + self.batch_size]
            embeddings = self.model.encode(
                batch,
                show_progress_bar=False,
                normalize_embeddings=True,  # L2归一化，cosine = dot product
            )
            all_embeddings.append(embeddings)

        return np.vstack(all_embeddings)

    def _compute_similarities(self, embeddings: np.ndarray) -> List[float]:
        """
        计算相邻句子间的余弦相似度

        Returns:
            长度为 len(embeddings)-1 的相似度列表
            similarities[i] = cosine_sim(sentence[i], sentence[i+1])
        """
        if len(embeddings) < 2:
            return []

        # 已经L2归一化，dot product = cosine similarity
        similarities = []
        for i in range(len(embeddings) - 1):
            sim = float(np.dot(embeddings[i], embeddings[i + 1]))
            similarities.append(sim)

        return similarities

    def _find_breakpoints(self, similarities: List[float]) -> List[int]:
        """
        找到语义断点位置

        断点 = 相似度低于阈值的位置
        返回断点索引列表（表示在该句子之后切分）
        """
        breakpoints = []
        for i, sim in enumerate(similarities):
            if sim < self.similarity_threshold:
                breakpoints.append(i)
        return breakpoints

    def _merge_short_chunks(self, chunks: List[List[str]]) -> List[List[str]]:
        """合并过短的chunk到相邻chunk"""
        if not chunks:
            return chunks

        merged = []
        buffer = []

        for chunk_sentences in chunks:
            chunk_text_len = sum(len(s) for s in chunk_sentences)

            if chunk_text_len < self.min_chunk_size and buffer:
                # 过短，合并到前一个
                buffer.extend(chunk_sentences)
            elif chunk_text_len < self.min_chunk_size and merged:
                # 过短且没有buffer，合并到上一个已完成的chunk
                merged[-1].extend(chunk_sentences)
            else:
                if buffer:
                    merged.append(buffer)
                    buffer = []
                buffer = list(chunk_sentences)

        if buffer:
            if merged and sum(len(s) for s in buffer) < self.min_chunk_size:
                merged[-1].extend(buffer)
            else:
                merged.append(buffer)

        return merged

    def _split_long_chunk(self, text: str) -> List[str]:
        """
        拆分过长的chunk（> max_chunk_size）

        优先按段落边界拆分，其次按句子边界拆分。
        """
        if len(text) <= self.max_chunk_size:
            return [text]

        # 先尝试按段落拆分
        paragraphs = PARAGRAPH_SPLIT_PATTERN.split(text)
        if len(paragraphs) > 1:
            result = []
            current = ""
            for para in paragraphs:
                if len(current) + len(para) + 2 <= self.max_chunk_size:
                    current = current + "\n\n" + para if current else para
                else:
                    if current:
                        result.append(current)
                    if len(para) > self.max_chunk_size:
                        # 段落本身超长，按句子拆
                        result.extend(self._split_by_sentences_simple(para))
                    else:
                        current = para
                        continue
                    current = ""
            if current:
                result.append(current)
            return result

        # 按句子拆分
        return self._split_by_sentences_simple(text)

    def _split_by_sentences_simple(self, text: str) -> List[str]:
        """简单按句子边界拆分超长文本"""
        sentences = self._split_sentences(text)
        result = []
        current = ""

        for sent in sentences:
            # 单个句子本身超过max_chunk_size，按字符硬切
            if len(sent) > self.max_chunk_size:
                if current:
                    result.append(current)
                    current = ""
                result.extend(self._hard_split(sent))
                continue

            if len(current) + len(sent) + 1 <= self.max_chunk_size:
                current = current + sent if not current else current + sent
            else:
                if current:
                    result.append(current)
                current = sent

        if current:
            result.append(current)

        return result if result else self._hard_split(text)

    def _hard_split(self, text: str) -> List[str]:
        """按max_chunk_size硬切文本，尽量在标点/空格处断开"""
        if len(text) <= self.max_chunk_size:
            return [text]

        result = []
        start = 0
        while start < len(text):
            end = start + self.max_chunk_size
            if end >= len(text):
                result.append(text[start:])
                break

            # 在切割点附近找标点或空格作为断点（回退最多200字符）
            best_break = end
            for offset in range(min(200, end - start)):
                pos = end - offset
                if text[pos] in '。！？!?\n，,；;、 ':
                    best_break = pos + 1
                    break

            result.append(text[start:best_break])
            start = best_break

        return [r for r in result if r.strip()]

    def split(self, text: str) -> List[str]:
        """
        语义分割文本，返回chunk列表

        Args:
            text: 待分割的文本

        Returns:
            chunk文本列表
        """
        result = self.split_with_metadata(text)
        return [item["text"] for item in result]

    def split_with_metadata(self, text: str) -> List[Dict]:
        """
        语义分割，返回带元数据的chunk列表

        Returns:
            [{"text": ..., "start_sentence": ..., "end_sentence": ...,
              "sentence_count": ..., "avg_similarity": ...}, ...]
        """
        text = text.strip()
        if not text:
            return []

        # 文本太短，直接返回
        if len(text) <= self.max_chunk_size and len(text) >= self.min_chunk_size:
            return [{
                "text": text,
                "start_sentence": 0,
                "end_sentence": 0,
                "sentence_count": 1,
                "avg_similarity": 1.0,
            }]

        if len(text) < self.min_chunk_size:
            return []

        # Step 1: 分句
        sentences = self._split_sentences(text)
        if not sentences:
            return []

        if len(sentences) == 1:
            # 只有一个句子但可能超长
            chunks_text = self._split_long_chunk(sentences[0])
            return [{
                "text": ct,
                "start_sentence": 0,
                "end_sentence": 0,
                "sentence_count": 1,
                "avg_similarity": 1.0,
            } for ct in chunks_text if len(ct) >= self.min_chunk_size]

        # Step 2: 编码
        embeddings = self._encode_sentences(sentences)

        # Step 3: 计算相邻相似度
        similarities = self._compute_similarities(embeddings)

        # Step 4: 找断点
        breakpoints = self._find_breakpoints(similarities)

        # Step 5: 按断点切分句子组
        chunk_sentence_groups = []
        prev_idx = 0
        for bp in breakpoints:
            group = sentences[prev_idx:bp + 1]
            if group:
                chunk_sentence_groups.append(group)
            prev_idx = bp + 1
        # 最后一组
        if prev_idx < len(sentences):
            chunk_sentence_groups.append(sentences[prev_idx:])

        # 如果没有断点，所有句子作为一个chunk
        if not chunk_sentence_groups:
            chunk_sentence_groups = [sentences]

        # Step 6: 合并过短的chunk
        chunk_sentence_groups = self._merge_short_chunks(chunk_sentence_groups)

        # Step 7: 构建结果，处理过长chunk
        results = []
        sent_offset = 0

        for group in chunk_sentence_groups:
            chunk_text = "".join(group)
            group_len = len(group)

            # 计算该组内的平均相似度
            start_idx = sent_offset
            end_idx = sent_offset + group_len - 1
            group_sims = []
            for i in range(start_idx, min(end_idx, len(similarities))):
                group_sims.append(similarities[i])
            avg_sim = float(np.mean(group_sims)) if group_sims else 1.0

            # 检查是否超长
            if len(chunk_text) > self.max_chunk_size:
                sub_chunks = self._split_long_chunk(chunk_text)
                for sc in sub_chunks:
                    if len(sc) >= self.min_chunk_size:
                        results.append({
                            "text": sc,
                            "start_sentence": start_idx,
                            "end_sentence": end_idx,
                            "sentence_count": group_len,
                            "avg_similarity": avg_sim,
                        })
            else:
                if len(chunk_text) >= self.min_chunk_size:
                    results.append({
                        "text": chunk_text,
                        "start_sentence": start_idx,
                        "end_sentence": end_idx,
                        "sentence_count": group_len,
                        "avg_similarity": avg_sim,
                    })

            sent_offset += group_len

        # 安全网：强制拆分所有超过max_chunk_size的chunk
        final_results = []
        for item in results:
            if len(item["text"]) > self.max_chunk_size:
                sub_texts = self._hard_split(item["text"])
                for st in sub_texts:
                    if len(st) >= self.min_chunk_size:
                        final_results.append({
                            "text": st,
                            "start_sentence": item["start_sentence"],
                            "end_sentence": item["end_sentence"],
                            "sentence_count": item["sentence_count"],
                            "avg_similarity": item["avg_similarity"],
                        })
            else:
                final_results.append(item)

        return final_results


def create_splitter(
    similarity_threshold: float = 0.5,
    max_chunk_size: int = 1500,
    min_chunk_size: int = 100,
) -> SemanticSplitter:
    """工厂函数：创建语义分割器实例"""
    return SemanticSplitter(
        model_name="thenlper/gte-large-zh",
        similarity_threshold=similarity_threshold,
        max_chunk_size=max_chunk_size,
        min_chunk_size=min_chunk_size,
    )


# ─── CLI测试入口 ─────────────────────────────────────────

if __name__ == "__main__":
    import sys
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    parser = argparse.ArgumentParser(description="语义分割器测试")
    parser.add_argument("--text", type=str, help="直接输入文本")
    parser.add_argument("--file", type=str, help="从文件读取文本")
    parser.add_argument("--threshold", type=float, default=0.5, help="相似度阈值")
    parser.add_argument("--max-size", type=int, default=1500, help="最大chunk大小")
    parser.add_argument("--min-size", type=int, default=100, help="最小chunk大小")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        text = (
            "深蹲是一个非常重要的复合动作，它可以锻炼到股四头肌、臀大肌和腘绳肌。"
            "正确的深蹲姿势要求双脚与肩同宽，脚尖略微外展。"
            "下蹲时膝盖应该沿着脚尖方向移动，不要内扣。"
            "核心肌群需要保持收紧，脊柱保持中立位。"
            "蛋白质是肌肉修复和生长的关键营养素。"
            "一般建议力量训练者每天摄入1.6-2.2克/公斤体重的蛋白质。"
            "优质蛋白质来源包括鸡胸肉、鸡蛋、牛奶和豆制品。"
            "训练后30分钟内补充蛋白质可以促进肌肉恢复。"
        )

    splitter = create_splitter(
        similarity_threshold=args.threshold,
        max_chunk_size=args.max_size,
        min_chunk_size=args.min_size,
    )

    results = splitter.split_with_metadata(text)

    print(f"\n{'='*60}")
    print(f"语义分割结果")
    print(f"阈值: {args.threshold} | 最大: {args.max_size} | 最小: {args.min_size}")
    print(f"原文长度: {len(text)} 字符")
    print(f"分割为 {len(results)} 个chunks")
    print(f"{'='*60}")

    for i, chunk in enumerate(results):
        print(f"\n--- Chunk {i+1} ---")
        print(f"长度: {len(chunk['text'])} | 句子: {chunk['sentence_count']} | 平均相似度: {chunk['avg_similarity']:.3f}")
        preview = chunk["text"][:200] + "..." if len(chunk["text"]) > 200 else chunk["text"]
        print(f"内容: {preview}")
