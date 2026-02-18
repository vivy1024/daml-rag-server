#!/usr/bin/env python3
"""迁移Qdrant向量数据到远程（使用gRPC）"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import time

LOCAL_HOST = "fitness_qdrant"
LOCAL_PORT = 6333

REMOTE_HOST = "182.92.78.183"
REMOTE_GRPC_PORT = 32091  # TCP端口映射到6334 (gRPC)

COLLECTION_NAME = "fitness_exercises_v2"
BATCH_SIZE = 100

def main():
    print("=" * 60)
    print("Qdrant 数据迁移")
    print("=" * 60)
    
    # 连接本地和远程
    print("\n连接数据库...")
    local_client = QdrantClient(host=LOCAL_HOST, port=LOCAL_PORT)
    # 使用gRPC连接远程（prefer_grpc=True）
    remote_client = QdrantClient(
        host=REMOTE_HOST, 
        grpc_port=REMOTE_GRPC_PORT,
        prefer_grpc=True,
        timeout=120
    )
    
    # 检查本地collection
    print("\n检查本地数据...")
    try:
        local_info = local_client.get_collection(COLLECTION_NAME)
        local_count = local_info.points_count
        vector_size = local_info.config.params.vectors.size
        print(f"  本地: {local_count} 向量, 维度: {vector_size}")
    except Exception as e:
        print(f"  错误: {e}")
        return
    
    # 检查远程collection
    print("\n检查远程数据...")
    try:
        remote_info = remote_client.get_collection(COLLECTION_NAME)
        remote_count = remote_info.points_count
        print(f"  远程: {remote_count} 向量")
    except:
        print(f"  远程collection不存在，创建中...")
        remote_client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        remote_count = 0
        print(f"  已创建collection: {COLLECTION_NAME}")
    
    if remote_count >= local_count:
        print(f"\n远程数据已完整 ({remote_count} >= {local_count})")
        return
    
    # 迁移数据
    print(f"\n开始迁移 {local_count} 个向量...")
    
    offset = None
    migrated = 0
    
    while True:
        # 从本地获取一批数据
        result = local_client.scroll(
            collection_name=COLLECTION_NAME,
            limit=BATCH_SIZE,
            offset=offset,
            with_payload=True,
            with_vectors=True
        )
        
        points, next_offset = result
        
        if not points:
            break
        
        # 转换为PointStruct
        point_structs = []
        for p in points:
            point_structs.append(PointStruct(
                id=p.id,
                vector=p.vector,
                payload=p.payload
            ))
        
        # 上传到远程
        remote_client.upsert(
            collection_name=COLLECTION_NAME,
            points=point_structs
        )
        
        migrated += len(points)
        print(f"  进度: {migrated}/{local_count}")
        
        if next_offset is None:
            break
        offset = next_offset
    
    # 验证
    print("\n验证迁移结果...")
    remote_info = remote_client.get_collection(COLLECTION_NAME)
    final_count = remote_info.points_count
    print(f"  本地: {local_count} 向量")
    print(f"  远程: {final_count} 向量")
    
    if final_count >= local_count:
        print("\n✅ Qdrant迁移成功!")
    else:
        print(f"\n⚠️ 差异: {local_count - final_count} 向量")

if __name__ == "__main__":
    main()
