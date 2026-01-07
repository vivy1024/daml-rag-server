
#!/usr/bin/env python3
"""
向量化训练知识并导入Qdrant

读取training_knowledge_texts.json，使用BGE-M3编码，导入Qdrant数据库。

Author: 薛小川
Created: 2025-11-19
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
import requests
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from tqdm import tqdm

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class TrainingKnowledgeVectorizer:
    """训练知识向量化器"""
    
    def __init__(
        self,
        input_file: str,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        collection_name: str = "training_knowledge"
    ):
        """
        初始化
        
        Args:
            input_file: 输入JSON文件路径
            qdrant_host: Qdrant主机
            qdrant_port: Qdrant端口
            collection_name: 集合名称
        """
        self.input_file = Path(input_file)
        self.collection_name = collection_name
        
        # 初始化Qdrant客户端
        self.qdrant_client = QdrantClient(host=qdrant_host, port=qdrant_port)
        
        # 初始化BGE-M3模型
        print("🔄 加载BGE-M3模型...")
        from sentence_transformers import SentenceTransformer
        self.encoder = SentenceTransformer('BAAI/bge-m3')
        print("✅ BGE-M3模型加载成功")
        
        print(f"✅ 连接到Qdrant: {qdrant_host}:{qdrant_port}")
    
    def load_text_chunks(self) -> List[Dict[str, Any]]:
        """加载文本块"""
        with open(self.input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        chunks = data.get('chunks', [])
        print(f"✅ 加载文本块: {len(chunks)} 个")
        return chunks
    
    def encode_text(self, text: str) -> List[float]:
        """
        使用BGE-M3编码文本
        
        直接使用本地加载的BGE-M3模型
        """
        try:
            # 使用本地BGE-M3模型编码
            embedding = self.encoder.encode(text, normalize_embeddings=True)
            return embedding.tolist()
                
        except Exception as e:
            print(f"❌ 编码错误: {e}")
            # 如果编码失败，返回零向量（仅用于测试）
            print("⚠️  使用零向量（测试模式）")
            return [0.0] * 1024
    
    def create_collection(self):
        """创建Qdrant集合"""
        try:
            # 检查集合是否存在
            collections = self.qdrant_client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name in collection_names:
                print(f"⚠️  集合已存在: {self.collection_name}")
                response = input("是否删除并重新创建？(y/n): ")
                if response.lower() == 'y':
                    self.qdrant_client.delete_collection(self.collection_name)
                    print(f"✅ 删除集合: {self.collection_name}")
                else:
                    print("⚠️  跳过创建集合")
                    return
            
            # 创建集合
            self.qdrant_client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1024,  # BGE-M3向量维度
                    distance=Distance.COSINE
                )
            )
            print(f"✅ 创建集合: {self.collection_name} (1024维, Cosine距离)")
            
        except Exception as e:
            print(f"❌ 创建集合失败: {e}")
            raise
    
    def vectorize_and_import(self, chunks: List[Dict[str, Any]]):
        """向量化并导入"""
        points = []
        
        print("\n🚀 开始向量化...")
        for i, chunk in enumerate(tqdm(chunks, desc="向量化进度")):
            chunk_id = chunk.get('id', f'chunk_{i}')
            text = chunk.get('text', '')
            metadata = chunk.get('metadata', {})
            
            # 编码文本
            vector = self.encode_text(text)
            
            if not vector or len(vector) != 1024:
                print(f"⚠️  跳过无效向量: {chunk_id}")
                continue
            
            # 创建Point
            point = PointStruct(
                id=i,
                vector=vector,
                payload={
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata
                }
            )
            points.append(point)
        
        # 批量导入
        if points:
            print(f"\n📤 导入Qdrant: {len(points)} 个向量...")
            self.qdrant_client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            print(f"✅ 导入完成: {len(points)} 个向量")
        else:
            print("❌ 没有有效向量可导入")
    
    def verify_import(self):
        """验证导入"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            print(f"\n📊 集合信息:")
            print(f"  - 名称: {collection_info.config.params.vectors.size}")
            print(f"  - 向量数: {collection_info.points_count}")
            print(f"  - 向量维度: {collection_info.config.params.vectors.size}")
            print(f"  - 距离度量: {collection_info.config.params.vectors.distance}")
            
            # 测试检索
            print(f"\n🔍 测试检索...")
            test_query = "什么是线性周期化？"
            query_vector = self.encode_text(test_query)
            
            if query_vector and len(query_vector) == 1024:
                results = self.qdrant_client.search(
                    collection_name=self.collection_name,
                    query_vector=query_vector,
                    limit=3
                )
                
                print(f"\n查询: {test_query}")
                print(f"结果数: {len(results)}")
                for i, result in enumerate(results, 1):
                    print(f"\n{i}. Score: {result.score:.4f}")
                    print(f"   ID: {result.payload.get('chunk_id')}")
                    print(f"   Text: {result.payload.get('text', '')[:100]}...")
            else:
                print("⚠️  无法生成查询向量，跳过检索测试")
                
        except Exception as e:
            print(f"❌ 验证失败: {e}")
    
    def run(self):
        """执行完整流程"""
        print("=" * 60)
        print("🚀 开始向量化并导入训练知识")
        print("=" * 60)
        
        # 1. 加载文本块
        chunks = self.load_text_chunks()
        
        # 2. 创建集合
        self.create_collection()
        
        # 3. 向量化并导入
        self.vectorize_and_import(chunks)
        
        # 4. 验证导入
        self.verify_import()
        
        print("\n" + "=" * 60)
        print("✅ 训练知识向量化并导入完成！")
        print("=" * 60)


def main():
    """主函数"""
    # 配置路径
    base_dir = Path(__file__).parent.parent.parent.parent
    input_file = base_dir / "perfect_enhanced_dataset" / "training_knowledge" / "training_knowledge_texts.json"
    
    # 检查输入文件
    if not input_file.exists():
        print(f"❌ 输入文件不存在: {input_file}")
        print("请先运行 prepare_training_knowledge_texts.py")
        return
    
    # 执行
    vectorizer = TrainingKnowledgeVectorizer(
        input_file=str(input_file),
        qdrant_host="localhost",
        qdrant_port=6333,
        collection_name="training_knowledge"
    )
    vectorizer.run()


if __name__ == "__main__":
    main()
