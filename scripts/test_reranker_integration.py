"""
Reranker 集成测试 - 验证在三层检索引擎中的工作情况
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, "/app")

# 设置环境变量
os.environ["ENABLE_RERANKER"] = "true"

from src.framework.retrieval.true_three_layer_engine import TrueThreeLayerEngine, LayerExecutionResult
from datetime import datetime

def test_reranker_in_engine():
    """测试 Reranker 在三层检索引擎中的集成"""
    print("\n" + "="*60)
    print("Reranker 集成测试")
    print("="*60)
    
    # 创建引擎实例
    engine = TrueThreeLayerEngine()
    
    # 模拟三层检索结果
    layer1_results = [
        {"id": "ex_001", "name": "深蹲", "content": "深蹲是复合动作", "score": 0.85},
        {"id": "ex_002", "name": "硬拉", "content": "硬拉是力量训练", "score": 0.75},
        {"id": "ex_003", "name": "卧推", "content": "卧推是胸部训练", "score": 0.70},
        {"id": "ex_004", "name": "引体向上", "content": "引体向上是背部训练", "score": 0.65},
        {"id": "ex_005", "name": "箭步蹲", "content": "箭步蹲是单腿训练", "score": 0.60},
    ]
    
    layer1 = LayerExecutionResult(
        layer_name="Layer1-Vector",
        success=True,
        results=layer1_results,
        execution_time_ms=100.0,
        confidence=0.8
    )
    
    layer2 = LayerExecutionResult(
        layer_name="Layer2-Graph",
        success=True,
        results=layer1_results[:3],
        execution_time_ms=150.0,
        confidence=0.7
    )
    
    layer3 = LayerExecutionResult(
        layer_name="Layer3-Rules",
        success=True,
        results=layer1_results[:5],
        execution_time_ms=50.0,
        confidence=0.9
    )
    
    # 调用 _build_final_result 方法
    query = "深蹲的正确姿势和常见错误"
    start_time = datetime.now()
    
    print(f"\n查询: {query}")
    print(f"Layer3 原始结果数量: {len(layer3.results)}")
    print("原始排序:")
    for i, doc in enumerate(layer3.results, 1):
        print(f"  {i}. {doc[\"name\"]} (分数: {doc[\"score\"]:.2f})")
    
    # 构建最终结果（会触发 Reranker）
    result = engine._build_final_result(
        query=query,
        domain="exercise",
        layer1=layer1,
        layer2=layer2,
        layer3=layer3,
        start_time=start_time
    )
    
    print(f"\n✅ 最终结果数量: {len(result.final_results)}")
    print(f"推理过程: {result.reasoning}")
    print("\nReranker 重排序后:")
    for i, doc in enumerate(result.final_results, 1):
        rerank_score = doc.get("rerank_score")
        if rerank_score is not None:
            print(f"  {i}. {doc[\"name\"]} (Rerank分数: {rerank_score:.3f}, 原始分数: {doc[\"score\"]:.2f})")
        else:
            print(f"  {i}. {doc[\"name\"]} (原始分数: {doc[\"score\"]:.2f})")
    
    # 验证 Reranker 是否被调用
    if "Reranker重排序" in result.reasoning:
        print("\n✅ Reranker 已成功集成到三层检索引擎")
    else:
        print("\n⚠️ Reranker 未被调用")
    
    print("\n" + "="*60)
    print("集成测试完成")
    print("="*60)

if __name__ == "__main__":
    test_reranker_in_engine()
