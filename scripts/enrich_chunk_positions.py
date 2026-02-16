#!/usr/bin/env python3
"""
Chunk位置元数据增强脚本
为Qdrant中的每个chunk添加位置信息，用于引用溯源
"""
import re
from typing import Dict, List
from qdrant_client import QdrantClient
from tqdm import tqdm


def extract_section_from_text(text: str) -> str:
    """从chunk文本提取章节标题"""
    lines = text.split('\n')
    for line in lines[:5]:  # 只检查前5行
        line = line.strip()
        # 匹配 Markdown 标题
        if line.startswith('#'):
            return line.lstrip('#').strip()
        # 匹配 Chapter X
        if re.match(r'^Chapter\s+\d+', line, re.IGNORECASE):
            return line
        # 匹配 第X章
        if re.match(r'^第[一二三四五六七八九十\d]+章', line):
            return line
    return ""


def estimate_position(chunk_index: int, total_chunks: int) -> Dict:
    """估算chunk在文档中的位置"""
    if total_chunks <= 1:
        return {
            "position_ratio": 0.5,
            "position_label": "全文"
        }

    ratio = chunk_index / max(total_chunks - 1, 1)

    if ratio < 0.2:
        label = "开头"
    elif ratio < 0.4:
        label = "前部"
    elif ratio < 0.6:
        label = "中间"
    elif ratio < 0.8:
        label = "后部"
    else:
        label = "结尾"

    return {
        "position_ratio": round(ratio, 3),
        "position_label": label
    }


def enrich_chunk_metadata(client: QdrantClient, collection_name: str, batch_size: int = 100):
    """批量增强chunk位置元数据"""

    # 获取集合信息
    collection_info = client.get_collection(collection_name)
    total_points = collection_info.points_count
    print(f"集合 {collection_name} 共有 {total_points} 个向量")

    # 滚动获取所有点
    offset = None
    processed = 0
    updated = 0

    with tqdm(total=total_points, desc="增强位置元数据") as pbar:
        while True:
            # 滚动获取
            results = client.scroll(
                collection_name=collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points, next_offset = results
            if not points:
                break

            # 批量更新
            updates = []
            for point in points:
                payload = point.payload
                chunk_index = payload.get('chunk_index', 0)
                total_chunks = payload.get('total_chunks', 1)
                source = payload.get('source', '')
                text = payload.get('chunk_text', payload.get('text', ''))

                # 提取章节路径
                section = extract_section_from_text(text)

                # 估算位置
                position_info = estimate_position(chunk_index, total_chunks)

                # 构建新的payload字段
                new_fields = {
                    'section_path': section,
                    'position_ratio': position_info['position_ratio'],
                    'position_label': position_info['position_label'],
                    'char_offset_start': chunk_index * 500,  # 估算值
                    'char_offset_end': (chunk_index + 1) * 500,
                    'paragraph_index': chunk_index,
                }

                # 对于B站字幕，添加时间戳估算
                if source == 'bilibili_subtitle':
                    # 假设每个chunk约30秒
                    new_fields['timestamp_start'] = chunk_index * 30
                    new_fields['timestamp_end'] = (chunk_index + 1) * 30

                # 添加source_type（如果缺失）
                if 'source_type' not in payload or not payload['source_type']:
                    if source == 'bilibili_subtitle':
                        new_fields['source_type'] = 'video'
                    elif 'pdf' in source.lower():
                        new_fields['source_type'] = 'pdf'
                    elif 'md' in source.lower() or 'markdown' in source.lower():
                        new_fields['source_type'] = 'markdown'
                    else:
                        new_fields['source_type'] = 'text'

                updates.append({
                    'id': point.id,
                    'payload': new_fields
                })

            # 批量更新到Qdrant
            if updates:
                for update in updates:
                    client.set_payload(
                        collection_name=collection_name,
                        payload=update['payload'],
                        points=[update['id']],
                    )
                updated += len(updates)

            processed += len(points)
            pbar.update(len(points))

            # 检查是否还有更多数据
            if next_offset is None:
                break
            offset = next_offset

    print(f"\n✅ 完成！处理 {processed} 个点，更新 {updated} 个点")
    return processed, updated


def verify_enrichment(client: QdrantClient, collection_name: str, sample_size: int = 5):
    """验证位置元数据增强结果"""
    print(f"\n验证位置元数据（随机抽样 {sample_size} 个）：")

    results = client.query_points(
        collection_name=collection_name,
        query=[0.0] * 1024,
        limit=sample_size,
        with_payload=True,
    )

    for i, point in enumerate(results.points):
        payload = point.payload
        print(f"\n=== 样本 {i+1} ===")
        print(f"文档: {payload.get('doc_title', 'N/A')}")
        print(f"来源: {payload.get('source', 'N/A')}")
        print(f"来源类型: {payload.get('source_type', 'N/A')}")
        print(f"Chunk索引: {payload.get('chunk_index', 'N/A')}/{payload.get('total_chunks', 'N/A')}")
        print(f"章节路径: {payload.get('section_path', 'N/A')}")
        print(f"位置标签: {payload.get('position_label', 'N/A')}")
        print(f"位置比例: {payload.get('position_ratio', 'N/A')}")
        if 'timestamp_start' in payload:
            print(f"时间戳: {payload['timestamp_start']}s - {payload['timestamp_end']}s")


def main():
    """主函数"""
    # 连接Qdrant（容器内用服务名）
    client = QdrantClient(host='qdrant', port=6333)
    collection_name = 'training_knowledge'

    print("=" * 60)
    print("Chunk位置元数据增强脚本")
    print("=" * 60)

    # 增强元数据
    processed, updated = enrich_chunk_metadata(client, collection_name)

    # 验证结果
    verify_enrichment(client, collection_name)

    print("\n" + "=" * 60)
    print(f"✅ 位置元数据增强完成！")
    print(f"   处理: {processed} 个chunk")
    print(f"   更新: {updated} 个chunk")
    print("=" * 60)


if __name__ == '__main__':
    main()
