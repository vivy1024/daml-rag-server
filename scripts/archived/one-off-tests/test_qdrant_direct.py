"""
直接测试Qdrant向量检索
验证智能过滤是否在Layer 1生效
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from framework.retrieval.graph.vector_search_engine import VectorSearchEngine

def test_qdrant_direct():
    """直接测试Qdrant向量检索"""
    print("=" * 80)
    print("直接测试Qdrant向量检索（Layer 1）")
    print("=" * 80)
    
    try:
        # 初始化VectorSearchEngine
        vector_search = VectorSearchEngine(
            host="fitness_qdrant",
            port=6333,
            collection_name="fitness_exercises_v2",
            vector_size=1024
        )
        print("✅ VectorSearchEngine初始化成功")
        print()
        
        # 测试1：不带智能过滤的查询
        print("【测试1】不带智能过滤的查询")
        print("-" * 80)
        results1 = vector_search.search_by_text(
            query="胸部",
            top_k=10,
            filter=None
        )
        print(f"返回结果数量: {len(results1)}")
        has_yoga1 = False
        for i, result in enumerate(results1[:5], 1):
            payload = result.get("payload", {})
            name = payload.get("name_zh", "未知")
            equipment = payload.get("equipment_zh", "未知")
            score = result.get("score", 0)
            print(f"{i}. {name} (器械: {equipment}, 相似度: {score:.4f})")
            if name == "山":
                has_yoga1 = True
                print("   ⚠️ 发现瑜伽动作！")
        print()
        
        # 测试2：带智能过滤的查询
        print("【测试2】带智能过滤的查询（包含'训练'关键词）")
        print("-" * 80)
        results2 = vector_search.search_by_text(
            query="胸部训练动作",
            top_k=10,
            filter=None
        )
        print(f"返回结果数量: {len(results2)}")
        has_yoga2 = False
        for i, result in enumerate(results2[:5], 1):
            payload = result.get("payload", {})
            name = payload.get("name_zh", "未知")
            equipment = payload.get("equipment_zh", "未知")
            score = result.get("score", 0)
            print(f"{i}. {name} (器械: {equipment}, 相似度: {score:.4f})")
            if name == "山":
                has_yoga2 = True
                print("   ⚠️ 发现瑜伽动作！")
        print()
        
        # 总结
        print("=" * 80)
        print("测试总结")
        print("=" * 80)
        if has_yoga1:
            print("测试1（不带'训练'关键词）: ❌ 返回了瑜伽动作（预期行为）")
        else:
            print("测试1（不带'训练'关键词）: ✅ 未返回瑜伽动作")
        
        if has_yoga2:
            print("测试2（带'训练'关键词）: ❌ 智能过滤失败，仍返回瑜伽动作")
        else:
            print("测试2（带'训练'关键词）: ✅ 智能过滤成功，已排除瑜伽动作")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_qdrant_direct()
