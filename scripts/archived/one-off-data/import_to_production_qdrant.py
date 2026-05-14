#!/usr/bin/env python3
"""
在生产环境中导入Exercise数据到Qdrant

直接在Zeabur的DAML-RAG容器中运行，使用内网Qdrant地址
注意：需要先设置环境变量QDRANT_API_KEY
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, '/app')

def main():
    print("=" * 60)
    print("🚀 开始导入Exercise数据到生产环境Qdrant")
    print("=" * 60)
    
    # 从环境变量获取配置
    qdrant_host = os.getenv('QDRANT_HOST', 'fitness_qdrant.zeabur.internal')
    qdrant_port = int(os.getenv('QDRANT_PORT', '6333'))
    qdrant_api_key = os.getenv('QDRANT_API_KEY')
    
    if not qdrant_api_key:
        print("❌ 错误：未设置QDRANT_API_KEY环境变量")
        print("请在Zeabur环境变量中设置QDRANT_API_KEY")
        return
    
    print(f"Qdrant地址: {qdrant_host}:{qdrant_port}")
    print(f"使用API Key认证: {qdrant_api_key[:10]}...")
    print()
    
    # 导入Exercise数据
    print("📥 导入Exercise数据...")
    try:
        from scripts.数据导入向量化.import_exercises_to_qdrant import ExerciseQdrantImporter
        
        exercise_importer = ExerciseQdrantImporter(
            data_file='/app/data/enhanced_perfect_exercises_dataset.json',
            qdrant_host=qdrant_host,
            qdrant_port=qdrant_port,
            qdrant_api_key=qdrant_api_key,  # 添加API Key
            collection_name='fitness_exercises_v2',
            vector_size=1024,
            embedding_model='thenlper/gte-large-zh'
        )
        exercise_importer.run(recreate=False)
        print("✅ Exercise数据导入完成")
    except Exception as e:
        print(f"❌ Exercise数据导入失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("=" * 60)
    print("✅ 导入完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
