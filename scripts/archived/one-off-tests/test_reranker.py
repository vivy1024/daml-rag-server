"""
Reranker 重排序模块测试脚本

测试内容:
1. 模型加载测试
2. 单次rerank测试
3. RRF融合测试
4. 性能测试
5. 对比测试（reranker前后的检索质量）
"""
import sys
import os
import time
import logging
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, '/app')

from src.framework.retrieval.reranker import FitnessReranker, get_reranker

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 测试查询（中文健身领域）
TEST_QUERIES = [
    "深蹲的正确姿势和常见错误",
    "肩部训练计划推荐",
    "减脂期间的蛋白质摄入量",
    "腰椎间盘突出可以做什么运动",
    "增肌训练的周期化安排"
]

# 模拟检索结果
MOCK_DOCUMENTS = [
    {
        "id": "ex_001",
        "name": "深蹲",
        "content": "深蹲是一种复合动作，主要锻炼股四头肌、臀大肌和核心肌群。正确姿势包括：双脚与肩同宽，膝盖不超过脚尖，背部保持挺直。",
        "score": 0.85
    },
    {
        "id": "ex_002",
        "name": "硬拉",
        "content": "硬拉是力量训练的基础动作，主要锻炼背部、臀部和腿部肌群。",
        "score": 0.75
    },
    {
        "id": "ex_003",
        "name": "卧推",
        "content": "卧推是胸部训练的经典动作，主要锻炼胸大肌、三角肌前束和肱三头肌。",
        "score": 0.70
    },
    {
        "id": "ex_004",
        "name": "引体向上",
        "content": "引体向上是背部训练的王牌动作，主要锻炼背阔肌和肱二头肌。",
        "score": 0.65
    },
    {
        "id": "ex_005",
        "name": "箭步蹲",
        "content": "箭步蹲是单腿训练动作，可以改善腿部力量不平衡，锻炼股四头肌和臀大肌。",
        "score": 0.60
    },
    {
        "id": "ex_006",
        "name": "推举",
        "content": "肩部推举是肩部训练的核心动作，主要锻炼三角肌中束和前束。",
        "score": 0.55
    },
    {
        "id": "ex_007",
        "name": "侧平举",
        "content": "侧平举是孤立训练三角肌中束的动作，可以增加肩部宽度。",
        "score": 0.50
    },
    {
        "id": "ex_008",
        "name": "俯身飞鸟",
        "content": "俯身飞鸟主要锻炼三角肌后束和上背部肌群。",
        "score": 0.45
    },
    {
        "id": "ex_009",
        "name": "平板支撑",
        "content": "平板支撑是核心训练的基础动作，可以增强核心稳定性。",
        "score": 0.40
    },
    {
        "id": "ex_010",
        "name": "俯卧撑",
        "content": "俯卧撑是徒手训练的经典动作，主要锻炼胸部、肩部和手臂。",
        "score": 0.35
    }
]


def test_model_loading():
    """测试1: 模型加载"""
    print("\n" + "="*60)
    print("测试1: 模型加载")
    print("="*60)
    
    try:
        start_time = time.time()
        reranker = get_reranker()
        load_time = time.time() - start_time
        
        print(f"✅ 模型加载成功")
        print(f"   模型名称: {reranker.model_name}")
        print(f"   设备: {reranker.device}")
        print(f"   加载时间: {load_time:.2f}秒")
        return True
    except Exception as e:
        print(f"❌ 模型加载失败: {e}")
        return False


def test_single_rerank():
    """测试2: 单次rerank测试"""
    print("\n" + "="*60)
    print("测试2: 单次Rerank测试")
    print("="*60)
    
    reranker = get_reranker()
    
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"\n查询 {i}: {query}")
        print("-" * 60)
        
        try:
            start_time = time.time()
            reranked_results = reranker.rerank(
                query=query,
                documents=MOCK_DOCUMENTS.copy(),
                top_k=5,
                score_threshold=0.0
            )
            rerank_time = (time.time() - start_time) * 1000
            
            print(f"✅ Rerank完成，耗时: {rerank_time:.2f}ms")
            print(f"   结果数量: {len(reranked_results)}")
            print(f"   Top 5 结果:")
            
            for j, doc in enumerate(reranked_results[:5], 1):
                print(f"   {j}. {doc['name']} (原始分数: {doc['score']:.2f}, Rerank分数: {doc['rerank_score']:.3f})")
                
        except Exception as e:
            print(f"❌ Rerank失败: {e}")


def test_rrf_fusion():
    """测试3: RRF融合测试"""
    print("\n" + "="*60)
    print("测试3: RRF融合测试")
    print("="*60)
    
    # 模拟3个不同来源的检索结果
    result_list_1 = MOCK_DOCUMENTS[:5]  # 向量检索结果
    result_list_2 = MOCK_DOCUMENTS[3:8]  # 图谱检索结果
    result_list_3 = MOCK_DOCUMENTS[5:10]  # 规则检索结果
    
    print(f"输入:")
    print(f"  列表1: {len(result_list_1)} 个结果")
    print(f"  列表2: {len(result_list_2)} 个结果")
    print(f"  列表3: {len(result_list_3)} 个结果")
    
    try:
        start_time = time.time()
        fused_results = FitnessReranker.rrf_fusion(
            result_lists=[result_list_1, result_list_2, result_list_3],
            k=60
        )
        fusion_time = (time.time() - start_time) * 1000
        
        print(f"\n✅ RRF融合完成，耗时: {fusion_time:.2f}ms")
        print(f"   融合后结果数量: {len(fused_results)}")
        print(f"   Top 5 结果:")
        
        for i, doc in enumerate(fused_results[:5], 1):
            print(f"   {i}. {doc['name']} (RRF分数: {doc['rrf_score']:.4f})")
            
    except Exception as e:
        print(f"❌ RRF融合失败: {e}")


def test_performance():
    """测试4: 性能测试"""
    print("\n" + "="*60)
    print("测试4: 性能测试")
    print("="*60)
    
    reranker = get_reranker()
    
    # 测试不同文档数量的性能
    doc_counts = [5, 10, 20, 50]
    
    for count in doc_counts:
        # 扩展文档列表
        extended_docs = MOCK_DOCUMENTS * (count // len(MOCK_DOCUMENTS) + 1)
        extended_docs = extended_docs[:count]
        
        times = []
        for _ in range(3):  # 每个测试运行3次
            start_time = time.time()
            reranker.rerank(
                query=TEST_QUERIES[0],
                documents=extended_docs,
                top_k=5
            )
            times.append((time.time() - start_time) * 1000)
        
        avg_time = sum(times) / len(times)
        print(f"文档数量: {count:3d}, 平均耗时: {avg_time:6.2f}ms")


def test_quality_comparison():
    """测试5: 质量对比测试"""
    print("\n" + "="*60)
    print("测试5: 质量对比测试（Reranker前后）")
    print("="*60)
    
    reranker = get_reranker()
    query = TEST_QUERIES[0]  # "深蹲的正确姿势和常见错误"
    
    print(f"\n查询: {query}")
    print("-" * 60)
    
    # 原始排序（按score降序）
    original_results = sorted(MOCK_DOCUMENTS.copy(), key=lambda x: x['score'], reverse=True)[:5]
    
    print("\n原始排序 (Top 5):")
    for i, doc in enumerate(original_results, 1):
        print(f"  {i}. {doc['name']} (分数: {doc['score']:.2f})")
    
    # Reranker重排序
    reranked_results = reranker.rerank(
        query=query,
        documents=MOCK_DOCUMENTS.copy(),
        top_k=5
    )
    
    print("\nReranker重排序 (Top 5):")
    for i, doc in enumerate(reranked_results, 1):
        print(f"  {i}. {doc['name']} (Rerank分数: {doc['rerank_score']:.3f}, 原始分数: {doc['score']:.2f})")
    
    # 分析变化
    print("\n排序变化分析:")
    original_names = [doc['name'] for doc in original_results]
    reranked_names = [doc['name'] for doc in reranked_results]
    
    for i, name in enumerate(reranked_names, 1):
        if name in original_names:
            original_rank = original_names.index(name) + 1
            if original_rank != i:
                print(f"  {name}: 排名 {original_rank} → {i}")
        else:
            print(f"  {name}: 新进入Top 5")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("Reranker 重排序模块测试")
    print("="*60)
    
    # 测试1: 模型加载
    if not test_model_loading():
        print("\n❌ 模型加载失败，终止测试")
        return
    
    # 测试2: 单次rerank
    test_single_rerank()
    
    # 测试3: RRF融合
    test_rrf_fusion()
    
    # 测试4: 性能测试
    test_performance()
    
    # 测试5: 质量对比
    test_quality_comparison()
    
    print("\n" + "="*60)
    print("✅ 所有测试完成")
    print("="*60)


if __name__ == "__main__":
    main()
