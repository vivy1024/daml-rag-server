#!/usr/bin/env python3
"""
引用溯源功能测试脚本（简化版）
直接使用Qdrant中的向量进行测试，不需要重新生成向量
"""
import sys
sys.path.insert(0, '/app')

from qdrant_client import QdrantClient
from src.framework.retrieval.citation_tracker import CitationTracker


def test_citation_formatting():
    """测试引用格式化功能"""
    print("=" * 80)
    print("引用溯源功能测试")
    print("=" * 80)

    # 初始化客户端
    print("\n1. 初始化Qdrant客户端...")
    client = QdrantClient(host='qdrant', port=6333)

    # 获取一些样本点作为测试数据
    print("\n2. 获取样本数据...")
    sample_results = client.scroll(
        collection_name='training_knowledge',
        limit=10,
        with_payload=True,
        with_vectors=False,
    )

    points = sample_results[0]
    print(f"   获取到 {len(points)} 个样本点")

    # 转换为检索结果格式
    search_results = []
    for i, point in enumerate(points):
        search_results.append({
            'payload': point.payload,
            'score': 0.9 - i * 0.05,  # 模拟相关度分数
        })

    # 初始化引用追踪器
    tracker = CitationTracker()

    # 测试1: 格式化引用
    print("\n" + "=" * 80)
    print("测试1: 格式化引用信息")
    print("=" * 80)
    citations = tracker.format_citations(search_results[:5])

    for citation in citations:
        print(f"\n[{citation['citation_id']}] {citation['doc_title']}")
        print(f"   来源类型: {citation['source_type']}")
        print(f"   章节: {citation['section_path'] or '无'}")
        print(f"   位置: {citation['position_label']} (chunk {citation['chunk_index']}/{citation['total_chunks']})")
        print(f"   位置比例: {citation['position_ratio']:.3f}")
        print(f"   相关度: {citation['relevance_score']:.4f}")
        print(f"   预览: {citation['text_preview'][:100]}...")

        # 视频来源显示时间戳
        if citation.get('bvid'):
            timestamp = citation.get('timestamp_start', 0)
            minutes = timestamp // 60
            seconds = timestamp % 60
            print(f"   视频时间: {minutes:02d}:{seconds:02d}")

    # 测试2: LLM格式
    print("\n" + "=" * 80)
    print("测试2: LLM格式（供综合阶段使用）")
    print("=" * 80)
    llm_format = tracker.format_for_llm(citations)
    print(llm_format)

    # 测试3: 前端格式
    print("\n" + "=" * 80)
    print("测试3: 前端格式（JSON）")
    print("=" * 80)
    frontend_format = tracker.format_for_frontend(citations)
    print(f"总来源数: {frontend_format['total_sources']}")
    print(f"总引用数: {frontend_format['total_citations']}")
    print(f"平均相关度: {frontend_format['avg_relevance']:.4f}")
    print(f"来源类型分布: {frontend_format['source_types']}")
    print(f"内容类型分布: {frontend_format['content_types']}")

    print("\n分组引用:")
    for doc_title, doc_citations in frontend_format['grouped_citations'].items():
        print(f"\n📚 {doc_title} ({len(doc_citations)}条引用)")
        for citation in doc_citations:
            print(f"   [{citation['citation_id']}] {citation['section_path'] or '无章节'} - {citation['position_label']}")

    # 测试4: 引用摘要
    print("\n" + "=" * 80)
    print("测试4: 引用摘要")
    print("=" * 80)
    summary = tracker.generate_citation_summary(citations)
    print(summary)

    # 测试5: 引用验证
    print("\n" + "=" * 80)
    print("测试5: 引用验证")
    print("=" * 80)
    test_answer = "根据资料[1]和[2]，深蹲时要注意姿势。参考[3]的建议..."
    validation = tracker.validate_citations(test_answer, citations)
    print(f"测试文本: {test_answer}")
    print(f"引用验证结果: {'✅ 有效' if validation['is_valid'] else '❌ 无效'}")
    print(f"使用的引用: {validation['used_citations']}/{validation['total_citations']}")
    if validation['invalid_citations']:
        print(f"无效引用ID: {validation['invalid_citations']}")

    # 测试6: 提取引用ID
    print("\n" + "=" * 80)
    print("测试6: 提取引用ID")
    print("=" * 80)
    extracted_ids = tracker.extract_citation_ids_from_text(test_answer)
    print(f"从文本中提取的引用ID: {extracted_ids}")


def test_position_metadata():
    """测试位置元数据"""
    print("\n" + "=" * 80)
    print("测试位置元数据增强结果")
    print("=" * 80)

    client = QdrantClient(host='qdrant', port=6333)

    # 获取不同位置的样本
    print("\n查询不同位置的chunk:")

    # 获取一些样本
    results = client.scroll(
        collection_name='training_knowledge',
        limit=20,
        with_payload=True,
        with_vectors=False,
    )

    points = results[0]

    # 按位置标签分组
    position_groups = {}
    for point in points:
        position_label = point.payload.get('position_label', '未知')
        if position_label not in position_groups:
            position_groups[position_label] = []
        position_groups[position_label].append(point)

    for position_label, group_points in sorted(position_groups.items()):
        print(f"\n位置: {position_label} ({len(group_points)}个)")
        for point in group_points[:2]:  # 每组只显示2个
            payload = point.payload
            print(f"  - {payload.get('doc_title', 'N/A')}")
            print(f"    Chunk: {payload.get('chunk_index', 0)}/{payload.get('total_chunks', 1)}")
            print(f"    位置比例: {payload.get('position_ratio', 0):.3f}")
            if payload.get('timestamp_start'):
                print(f"    时间戳: {payload['timestamp_start']}s")


def test_statistics():
    """测试统计信息"""
    print("\n" + "=" * 80)
    print("位置元数据统计")
    print("=" * 80)

    client = QdrantClient(host='qdrant', port=6333)

    # 获取所有点的位置标签统计
    print("\n统计位置标签分布...")

    position_counts = {}
    source_type_counts = {}

    offset = None
    total = 0

    while True:
        results = client.scroll(
            collection_name='training_knowledge',
            limit=100,
            offset=offset,
            with_payload=True,
            with_vectors=False,
        )

        points, next_offset = results
        if not points:
            break

        for point in points:
            payload = point.payload
            position_label = payload.get('position_label', '未知')
            source_type = payload.get('source_type', '未知')

            position_counts[position_label] = position_counts.get(position_label, 0) + 1
            source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
            total += 1

        if next_offset is None:
            break
        offset = next_offset

        if total >= 1000:  # 只统计前1000个
            break

    print(f"\n总计统计: {total} 个chunk")

    print("\n位置标签分布:")
    for label, count in sorted(position_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / total * 100
        print(f"  {label}: {count} ({percentage:.1f}%)")

    print("\n来源类型分布:")
    for source_type, count in sorted(source_type_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = count / total * 100
        print(f"  {source_type}: {count} ({percentage:.1f}%)")


def main():
    """主函数"""
    try:
        # 测试1: 引用格式化
        test_citation_formatting()

        # 测试2: 位置元数据
        test_position_metadata()

        # 测试3: 统计信息
        test_statistics()

        print("\n" + "=" * 80)
        print("✅ 所有测试完成！")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
