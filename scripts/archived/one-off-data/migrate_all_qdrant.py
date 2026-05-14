#!/usr/bin/env python3
"""迁移所有Qdrant集合到远程"""
import os
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

LOCAL_HOST = "fitness_qdrant"
LOCAL_PORT = 6333
REMOTE_HOST = "182.92.78.183"
REMOTE_GRPC_PORT = 32091
REMOTE_API_KEY = os.environ.get("QDRANT_API_KEY", "yuzhen_qdrant_2025_secure_abc123xyz789")
BATCH_SIZE = 100

def migrate_collection(local_client, remote_client, name):
    """迁移单个集合"""
    try:
        info = local_client.get_collection(name)
        count = info.points_count
        if count == 0:
            print(f"  {name}: 空集合，跳过")
            return
        
        vector_size = info.config.params.vectors.size
        print(f"  {name}: {count} 向量, 维度 {vector_size}")
        
        # 检查远程是否存在
        try:
            remote_info = remote_client.get_collection(name)
            remote_count = remote_info.points_count
            if remote_count >= count:
                print(f"    远程已有 {remote_count} 向量，跳过")
                return
        except:
            remote_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            print(f"    创建远程集合")
        
        # 迁移数据
        offset = None
        migrated = 0
        while True:
            result = local_client.scroll(name, limit=BATCH_SIZE, offset=offset, 
                                         with_payload=True, with_vectors=True)
            points, next_offset = result
            if not points:
                break
            
            point_structs = [PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points]
            remote_client.upsert(collection_name=name, points=point_structs)
            migrated += len(points)
            
            if next_offset is None:
                break
            offset = next_offset
        
        print(f"    迁移完成: {migrated} 向量")
    except Exception as e:
        print(f"    错误: {e}")

def main():
    print("=" * 50)
    print("迁移所有Qdrant集合")
    print("=" * 50)
    
    local = QdrantClient(host=LOCAL_HOST, port=LOCAL_PORT)
    remote = QdrantClient(host=REMOTE_HOST, grpc_port=REMOTE_GRPC_PORT, prefer_grpc=True, timeout=120, api_key=REMOTE_API_KEY, https=False)
    
    collections = local.get_collections()
    for c in collections.collections:
        migrate_collection(local, remote, c.name)
    
    # 验证
    print("\n远程集合状态:")
    for c in remote.get_collections().collections:
        info = remote.get_collection(c.name)
        print(f"  {c.name}: {info.points_count} 向量")

if __name__ == "__main__":
    main()
