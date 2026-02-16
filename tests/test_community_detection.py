"""
社区检测功能测试
"""

import sys
sys.path.insert(0, '/app/src')

from framework.retrieval.community_retriever import CommunityRetriever


def test_community_retriever():
    """测试社区检索器"""
    print("=== 测试社区检索器 ===\n")
    
    retriever = CommunityRetriever()
    
    # 测试用例
    test_cases = [
        ("胸肌训练", 2),
        ("推类动作", 2),
        ("腹肌核心", 2),
        ("复合动作", 2),
        ("拉背训练", 2),
        ("腿部训练", 2),
    ]
    
    for query, top_k in test_cases:
        print(f"查询: {query}")
        results = retriever.get_community_context(query, top_k=top_k)
        
        if results:
            print(f"找到 {len(results)} 个相关社区:")
            for r in results:
                print(f"  - {r['name']}")
                print(f"    动作数: {r['exercise_count']}, 肌肉数: {r['muscle_count']}")
                print(f"    主要肌肉: {', '.join(r['primary_muscles'][:3])}")
        else:
            print("未找到相关社区")
        print()
    
    # 测试格式化输出
    print("=== 测试格式化输出 ===\n")
    results = retriever.get_community_context("胸肌训练", top_k=2)
    formatted = retriever.format_context(results)
    print(formatted)
    
    print("\n=== 测试通过 ===")


if __name__ == "__main__":
    test_community_retriever()
