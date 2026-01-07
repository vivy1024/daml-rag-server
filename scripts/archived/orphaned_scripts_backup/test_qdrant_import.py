"""
Qdrant向量导入测试脚本

简单测试Qdrant向量导入功能

作者：薛小川
日期：2025-12-19
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入，避免通过__init__.py
import sys
sys.path.insert(0, str(project_root / "src"))

# 导入必要的模块
from framework.clients.qdrant_client import create_qdrant_client
from framework.models.model_cache_manager import ModelCacheManager

# 手动加载models.py
import importlib.util
models_spec = importlib.util.spec_from_file_location(
    "models",
    project_root / "src/applications/fitness/data_supplement/models.py"
)
models_module = importlib.util.module_from_spec(models_spec)
models_spec.loader.exec_module(models_module)
SupplementResult = models_module.SupplementResult

# 手动加载qdrant_importer.py
qdrant_spec = importlib.util.spec_from_file_location(
    "qdrant_importer",
    project_root / "src/applications/fitness/data_supplement/qdrant_importer.py"
)
qdrant_module = importlib.util.module_from_spec(qdrant_spec)

# 在加载前注入依赖
import qdrant_client.models
qdrant_module.SupplementResult = SupplementResult
qdrant_module.ModelCacheManager = ModelCacheManager
qdrant_module.QdrantClient = qdrant_client.QdrantClient
qdrant_module.PointStruct = qdrant_client.models.PointStruct
qdrant_module.VectorParams = qdrant_client.models.VectorParams
qdrant_module.Distance = qdrant_client.models.Distance

# 加载模块
qdrant_spec.loader.exec_module(qdrant_module)

# 再次注入（确保覆盖）
qdrant_module.SupplementResult = SupplementResult
qdrant_module.ModelCacheManager = ModelCacheManager

QdrantImporter = qdrant_module.QdrantImporter


def test_markdown_vectorization():
    """测试Markdown文件向量化"""
    print("\n" + "="*60)
    print("测试1: Markdown文件向量化")
    print("="*60)
    
    # 创建Qdrant客户端
    client = create_qdrant_client(
        host=os.getenv('QDRANT_HOST', 'qdrant'),
        port=int(os.getenv('QDRANT_PORT', '6333'))
    )
    
    # 创建导入器
    importer = QdrantImporter(
        qdrant_client=client,
        collection_name="test_training_knowledge",
        embedding_model="BAAI/bge-m3",
        vector_size=1024
    )
    
    # 测试文件
    test_file = "data/training_knowledge/recommendation_decision_tree.md"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return False
    
    # 向量化
    try:
        vectors = importer.vectorize_markdown(
            file_path=test_file,
            chunk_size=512,
            overlap=50
        )
        
        print(f"\n✅ 向量化成功:")
        print(f"  - 生成向量数: {len(vectors)}")
        print(f"  - 向量维度: {len(vectors[0]['vector'])}")
        print(f"  - 第一个向量ID: {vectors[0]['id']}")
        print(f"  - 第一个向量文本长度: {len(vectors[0]['payload']['text'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ 向量化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_json_vectorization():
    """测试JSON文件向量化"""
    print("\n" + "="*60)
    print("测试2: JSON文件向量化")
    print("="*60)
    
    # 创建Qdrant客户端
    client = create_qdrant_client(
        host=os.getenv('QDRANT_HOST', 'qdrant'),
        port=int(os.getenv('QDRANT_PORT', '6333'))
    )
    
    # 创建导入器
    importer = QdrantImporter(
        qdrant_client=client,
        collection_name="test_training_knowledge",
        embedding_model="BAAI/bge-m3",
        vector_size=1024
    )
    
    # 测试文件
    test_file = "data/training_knowledge/training_knowledge_texts.json"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return False
    
    # 向量化
    try:
        vectors = importer.vectorize_json_texts(file_path=test_file)
        
        print(f"\n✅ 向量化成功:")
        print(f"  - 生成向量数: {len(vectors)}")
        print(f"  - 向量维度: {len(vectors[0]['vector'])}")
        print(f"  - 第一个向量ID: {vectors[0]['id']}")
        
        return True
        
    except Exception as e:
        print(f"❌ 向量化失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vector_upsert():
    """测试向量存储"""
    print("\n" + "="*60)
    print("测试3: 向量存储到Qdrant")
    print("="*60)
    
    # 创建Qdrant客户端
    client = create_qdrant_client(
        host=os.getenv('QDRANT_HOST', 'qdrant'),
        port=int(os.getenv('QDRANT_PORT', '6333'))
    )
    
    # 创建导入器
    importer = QdrantImporter(
        qdrant_client=client,
        collection_name="test_training_knowledge",
        embedding_model="BAAI/bge-m3",
        vector_size=1024
    )
    
    # 准备测试向量
    test_vectors = [
        {
            "id": "test_vector_1",
            "vector": [0.1] * 1024,
            "payload": {
                "type": "test",
                "source_file": "test.md",
                "chunk_index": 0,
                "text": "测试文本1",
                "created_at": "2025-12-19 00:00:00"
            }
        },
        {
            "id": "test_vector_2",
            "vector": [0.2] * 1024,
            "payload": {
                "type": "test",
                "source_file": "test.md",
                "chunk_index": 1,
                "text": "测试文本2",
                "created_at": "2025-12-19 00:00:00"
            }
        }
    ]
    
    try:
        # 第一次导入
        print("\n第一次导入...")
        result1 = importer.upsert_vectors(test_vectors)
        
        print(f"\n✅ 第一次导入成功:")
        print(f"  - 总数: {result1.total_nodes}")
        print(f"  - 新增: {result1.created_nodes}")
        print(f"  - 错误: {len(result1.errors)}")
        print(f"  - 耗时: {result1.execution_time:.2f}秒")
        
        # 第二次导入（测试幂等性）
        print("\n第二次导入（测试幂等性）...")
        result2 = importer.upsert_vectors(test_vectors)
        
        print(f"\n✅ 第二次导入成功:")
        print(f"  - 总数: {result2.total_nodes}")
        print(f"  - 新增: {result2.created_nodes}")
        print(f"  - 跳过: {result2.total_nodes - result2.created_nodes}")
        
        if result2.created_nodes == 0:
            print("\n✅ 幂等性测试通过: 第二次导入没有创建新向量")
            return True
        else:
            print("\n❌ 幂等性测试失败: 第二次导入创建了新向量")
            return False
        
    except Exception as e:
        print(f"❌ 向量存储失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_full_workflow():
    """测试完整工作流程"""
    print("\n" + "="*60)
    print("测试4: 完整工作流程")
    print("="*60)
    
    # 创建Qdrant客户端
    client = create_qdrant_client(
        host=os.getenv('QDRANT_HOST', 'qdrant'),
        port=int(os.getenv('QDRANT_PORT', '6333'))
    )
    
    # 创建导入器
    importer = QdrantImporter(
        qdrant_client=client,
        collection_name="test_training_knowledge",
        embedding_model="BAAI/bge-m3",
        vector_size=1024
    )
    
    # 测试文件
    test_file = "data/training_knowledge/user_profile_analysis_logic.md"
    
    if not os.path.exists(test_file):
        print(f"❌ 测试文件不存在: {test_file}")
        return False
    
    try:
        # 1. 向量化
        print("\n步骤1: 向量化Markdown文件...")
        vectors = importer.vectorize_markdown(
            file_path=test_file,
            chunk_size=512,
            overlap=50
        )
        print(f"✅ 向量化完成: {len(vectors)}个向量")
        
        # 2. 存储
        print("\n步骤2: 存储到Qdrant...")
        result = importer.upsert_vectors(vectors)
        
        print(f"\n✅ 完整工作流程测试成功:")
        print(f"  - 总数: {result.total_nodes}")
        print(f"  - 新增: {result.created_nodes}")
        print(f"  - 错误: {len(result.errors)}")
        print(f"  - 耗时: {result.execution_time:.2f}秒")
        
        return True
        
    except Exception as e:
        print(f"❌ 完整工作流程失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("\n" + "="*60)
    print("Qdrant向量导入测试")
    print("="*60)
    
    results = []
    
    # 运行所有测试
    results.append(("Markdown向量化", test_markdown_vectorization()))
    results.append(("JSON向量化", test_json_vectorization()))
    results.append(("向量存储", test_vector_upsert()))
    results.append(("完整工作流程", test_full_workflow()))
    
    # 输出总结
    print("\n" + "="*60)
    print("测试总结")
    print("="*60)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{name}: {status}")
    
    # 统计
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过!")
        return 0
    else:
        print(f"\n⚠️ {total - passed} 个测试失败")
        return 1


if __name__ == "__main__":
    sys.exit(main())
