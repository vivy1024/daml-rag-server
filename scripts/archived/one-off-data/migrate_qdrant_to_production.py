#!/usr/bin/env python3
"""迁移Qdrant集合到生产环境（支持API Key认证）"""
import os

# 禁用代理
os.environ['NO_PROXY'] = '*'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['http_proxy'] = ''
os.environ['https_proxy'] = ''

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# 本地Qdrant配置
LOCAL_HOST = "fitness_qdrant"  # Docker网络中的服务名
LOCAL_PORT = 6333

# 生产环境Qdrant配置
# 使用公网IP + HTTP端口 + API Key
# 注意：Zeabur公网端口32091是gRPC端口(6334)，我们需要找到HTTP端口(6333)的映射
# 如果没E_PORT = 6333  # HTTP端口
REMOTE_API_KEY = "yuzhen_qdrant_2025_secure_abc123xyz789"
BATCH_SIZE = 100

def migrate_collection(local_client, remote_client, name):
    """迁移单个集合"""
    try:
        print(f"\n{'='*60}")
        print(f"开始迁移集合: {name}")
        print(f"{'='*60}")
        
        # 获取本地集合信息
        info = local_client.get_collection(name)
        count = info.points_count
        vector_size = info.config.params.vectors.size
        
        print(f"  本地集合信息:")
        print(f"    - 向量数: {count}")
        print(f"    - 维度: {vector_size}")
        
        if count == 0:
            print(f"  ⚠️ 空集合，跳过")
            return
        
        # 检查远程集合
        try:
            remote_info = remote_client.get_collection(name)
            remote_count = remote_info.points_count
            print(f"  远程集合已存在:")
            print(f"    - 向量数: {remote_count}")
            
            if remote_count >= count:
                print(f"  ✅ 远程已有足够数据，跳过")
                return
            else:
                print(f"  🔄 远程数据不完整，开始迁移...")
        except Exception as e:
            print(f"  📦 远程集合不存在，创建中...")
            remote_client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )
            print(f"  ✅ 远程集合创建成功")
        
        # 迁移数据
        print(f"  🚀 开始迁移数据...")
        offset = None
        migrated = 0
        
        while True:
            # 从本地读取数据
            result = local_client.scroll(
                name, 
                limit=BATCH_SIZE, 
                offset=offset,
                with_payload=True, 
                with_vectors=True
            )
            points, next_offset = result
            
            if not points:
                break
            
            # 转换为PointStruct
            point_structs = [
                PointStruct(
                    id=p.id, 
                    vector=p.vector, 
                    payload=p.payload
                ) 
                for p in points
            ]
            
            # 上传到远程
            remote_client.upsert(collection_name=name, points=point_structs)
            migrated += len(points)
            
            print(f"    进度: {migrated}/{count} ({migrated * 100 // count}%)")
            
            if next_offset is None:
                break
            offset = next_offset
        
        print(f"  ✅ 迁移完成: {migrated} 个向量")
        
    except Exception as e:
        print(f"  ❌ 错误: {e}")
        import traceback
        traceback.print_exc()

def main():
    print("=" * 60)
    print("Qdrant数据迁移工具 - 本地 → 生产环境")
    print("=" * 60)
    print(f"本地: {LOCAL_HOST}:{LOCAL_PORT}")
    print(f"远程: {REMOTE_HOST}:{REMOTE_PORT} (HTTP + API Key)")
    print("=" * 60)
    
    # 连接本地Qdrant
    print("\n🔗 连接本地Qdrant...")
    local = QdrantClient(host=LOCAL_HOST, port=LOCAL_PORT)
    print("✅ 本地连接成功")
    
    # 连接远程Qdrant（使用HTTP + API Key）
    print("\n🔗 连接生产环境Qdrant...")
    remote = QdrantClient(
        host=REMOTE_HOST,
        port=REMOTE_PORT,
        api_key=REMOTE_API_KEY,
        https=False,  # 内网使用HTTP
        timeout=120
    )
    print("✅ 远程连接成功")
    
    # 获取本地集合列表
    print("\n📋 获取本地集合列表...")
    collections = local.get_collections()
    print(f"找到 {len(collections.collections)} 个集合")
    
    # 迁移每个集合
    for c in collections.collections:
        migrate_collection(local, remote, c.name)
    
    # 验证远程集合
    print("\n" + "=" * 60)
    print("验证远程集合状态")
    print("=" * 60)
    
    remote_collections = remote.get_collections()
    for c in remote_collections.collections:
        info = remote.get_collection(c.name)
        print(f"  {c.name}: {info.points_count} 个向量")
    
    print("\n" + "=" * 60)
    print("✅ 迁移完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
