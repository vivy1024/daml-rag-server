"""
Qdrant向量导入器测试

测试内容：
1. Markdown文件向量化
2. JSON文件向量化
3. 向量存储到Qdrant
4. 幂等性检查

作者：薛小川
日期：2025-12-19
"""

import pytest
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入模块，避免通过__init__.py
import importlib.util

# 加载QdrantImporter
spec = importlib.util.spec_from_file_location(
    "qdrant_importer",
    project_root / "src/applications/fitness/data_supplement/qdrant_importer.py"
)
qdrant_importer_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qdrant_importer_module)
QdrantImporter = qdrant_importer_module.QdrantImporter

from src.framework.clients.qdrant_client import create_qdrant_client


@pytest.fixture
def qdrant_client():
    """创建Qdrant客户端"""
    client = create_qdrant_client(
        host=os.getenv('QDRANT_HOST', 'qdrant'),
        port=int(os.getenv('QDRANT_PORT', '6333'))
    )
    return client


@pytest.fixture
def qdrant_importer(qdrant_client):
    """创建Qdrant导入器"""
    return QdrantImporter(
        qdrant_client=qdrant_client,
        collection_name="test_training_knowledge",
        embedding_model="BAAI/bge-m3",
        vector_size=1024
    )


def test_vectorize_markdown(qdrant_importer):
    """测试Markdown文件向量化"""
    # 准备测试文件路径
    test_file = "data/training_knowledge/recommendation_decision_tree.md"
    
    if not os.path.exists(test_file):
        pytest.skip(f"测试文件不存在: {test_file}")
    
    # 向量化
    vectors = qdrant_importer.vectorize_markdown(
        file_path=test_file,
        chunk_size=512,
        overlap=50
    )
    
    # 验证结果
    assert len(vectors) > 0, "应该生成至少一个向量"
    
    # 验证向量结构
    first_vector = vectors[0]
    assert "id" in first_vector
    assert "vector" in first_vector
    assert "payload" in first_vector
    
    # 验证向量维度
    assert len(first_vector["vector"]) == 1024, "向量维度应为1024"
    
    # 验证payload
    payload = first_vector["payload"]
    assert "type" in payload
    assert "source_file" in payload
    assert "chunk_index" in payload
    assert "text" in payload
    assert "created_at" in payload
    
    print(f"✅ Markdown向量化测试通过: 生成{len(vectors)}个向量")


def test_vectorize_json_texts(qdrant_importer):
    """测试JSON文件向量化"""
    # 准备测试文件路径
    test_file = "data/training_knowledge/training_knowledge_texts.json"
    
    if not os.path.exists(test_file):
        pytest.skip(f"测试文件不存在: {test_file}")
    
    # 向量化
    vectors = qdrant_importer.vectorize_json_texts(file_path=test_file)
    
    # 验证结果
    assert len(vectors) > 0, "应该生成至少一个向量"
    
    # 验证向量结构
    first_vector = vectors[0]
    assert "id" in first_vector
    assert "vector" in first_vector
    assert "payload" in first_vector
    
    # 验证向量维度
    assert len(first_vector["vector"]) == 1024, "向量维度应为1024"
    
    print(f"✅ JSON向量化测试通过: 生成{len(vectors)}个向量")


def test_upsert_vectors(qdrant_importer):
    """测试向量存储到Qdrant"""
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
    
    # 第一次导入
    result1 = qdrant_importer.upsert_vectors(test_vectors)
    
    # 验证结果
    assert result1.total_nodes == 2
    assert result1.created_nodes == 2
    assert len(result1.errors) == 0
    
    print(f"✅ 第一次导入成功: 创建{result1.created_nodes}个向量")
    
    # 第二次导入（测试幂等性）
    result2 = qdrant_importer.upsert_vectors(test_vectors)
    
    # 验证幂等性
    assert result2.total_nodes == 2
    assert result2.created_nodes == 0, "第二次导入不应创建新向量"
    
    print(f"✅ 幂等性测试通过: 跳过{result2.total_nodes}个已存在的向量")


def test_check_vector_exists(qdrant_importer):
    """测试向量存在性检查"""
    # 准备测试向量
    test_vector = {
        "id": "test_check_exists",
        "vector": [0.3] * 1024,
        "payload": {
            "type": "test",
            "source_file": "test.md",
            "chunk_index": 0,
            "text": "测试存在性检查",
            "created_at": "2025-12-19 00:00:00"
        }
    }
    
    # 检查不存在的向量
    exists_before = qdrant_importer.check_vector_exists("test_check_exists")
    assert not exists_before, "向量不应存在"
    
    # 导入向量
    qdrant_importer.upsert_vectors([test_vector])
    
    # 检查已存在的向量
    exists_after = qdrant_importer.check_vector_exists("test_check_exists")
    assert exists_after, "向量应该存在"
    
    print("✅ 向量存在性检查测试通过")


def test_full_workflow(qdrant_importer):
    """测试完整工作流程"""
    # 1. 向量化Markdown文件
    md_file = "data/training_knowledge/user_profile_analysis_logic.md"
    
    if not os.path.exists(md_file):
        pytest.skip(f"测试文件不存在: {md_file}")
    
    vectors = qdrant_importer.vectorize_markdown(
        file_path=md_file,
        chunk_size=512,
        overlap=50
    )
    
    print(f"📊 向量化完成: {len(vectors)}个向量")
    
    # 2. 存储到Qdrant
    result = qdrant_importer.upsert_vectors(vectors)
    
    print(f"📊 导入结果:")
    print(f"  - 总数: {result.total_nodes}")
    print(f"  - 新增: {result.created_nodes}")
    print(f"  - 错误: {len(result.errors)}")
    print(f"  - 耗时: {result.execution_time:.2f}秒")
    
    # 3. 验证导入成功
    assert result.total_nodes > 0
    assert len(result.errors) == 0
    
    print("✅ 完整工作流程测试通过")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "-s"])
