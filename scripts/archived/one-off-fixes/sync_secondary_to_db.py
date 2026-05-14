#!/usr/bin/env python3
"""
从JSON同步muscles_secondary字段到MySQL和Qdrant
以文件系统为准
"""
import asyncio
import json
import aiomysql
from qdrant_client import QdrantClient

async def sync_mysql(data):
    """同步到MySQL"""
    print("\n" + "="*60)
    print("MySQL: 同步muscles_secondary字段")
    print("="*60)
    
    conn = await aiomysql.connect(
        host='fitness_mysql', port=3306,
        user='fitness_user', password='fitness_pass',
        db='fitness_app'
    )
    
    updated = 0
    async with conn.cursor() as cursor:
        for eid_str, fields in data.items():
            eid = int(eid_str)
            sec_zh = fields.get('muscles_secondary_zh')
            sec_en = fields.get('muscles_secondary_en')
            
            await cursor.execute("""
                UPDATE exercises 
                SET muscles_secondary_zh = %s, muscles_secondary_en = %s
                WHERE id = %s
            """, (
                json.dumps(sec_zh, ensure_ascii=False) if sec_zh else None,
                json.dumps(sec_en, ensure_ascii=False) if sec_en else None,
                eid
            ))
            updated += 1
        
        await conn.commit()
    
    # 验证
    async with conn.cursor() as cursor:
        await cursor.execute('SELECT COUNT(*) FROM exercises WHERE muscles_secondary_zh IS NOT NULL')
        zh = (await cursor.fetchone())[0]
        await cursor.execute('SELECT COUNT(*) FROM exercises WHERE muscles_secondary_en IS NOT NULL')
        en = (await cursor.fetchone())[0]
        print(f"更新: {updated}条")
        print(f"验证: secondary_zh={zh}, secondary_en={en}")
    
    conn.close()


def sync_qdrant(data):
    """同步到Qdrant"""
    print("\n" + "="*60)
    print("Qdrant: 同步muscles_secondary字段")
    print("="*60)
    
    client = QdrantClient(host='qdrant', port=6333)
    updated = 0
    
    for eid_str, fields in data.items():
        eid = int(eid_str)
        
        # 查找point
        results, _ = client.scroll(
            collection_name="fitness_exercises_v2",
            scroll_filter={"must": [{"key": "id", "match": {"value": eid}}]},
            limit=1,
            with_payload=False
        )
        
        if results:
            point_id = results[0].id
            payload = {}
            
            sec_zh = fields.get('muscles_secondary_zh')
            sec_en = fields.get('muscles_secondary_en')
            
            # 设置值（包括None来清除错误数据）
            payload['muscles_secondary_zh'] = sec_zh if sec_zh else []
            payload['muscles_secondary_en'] = sec_en if sec_en else []
            
            client.set_payload(
                collection_name="fitness_exercises_v2",
                payload=payload,
                points=[point_id]
            )
            updated += 1
            
            if updated % 300 == 0:
                print(f"已更新 {updated} 个点...")
    
    # 验证
    total_zh = 0
    total_en = 0
    offset = None
    while True:
        results, next_offset = client.scroll('fitness_exercises_v2', limit=100, offset=offset, with_payload=True)
        if not results:
            break
        for r in results:
            if r.payload.get('muscles_secondary_zh'):
                total_zh += 1
            if r.payload.get('muscles_secondary_en'):
                total_en += 1
        offset = next_offset
        if offset is None:
            break
    
    print(f"更新: {updated}个点")
    print(f"验证: secondary_zh={total_zh}, secondary_en={total_en}")


async def main():
    # 读取JSON
    with open('/app/logs/secondary_muscles_sync.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"读取到 {len(data)} 条记录")
    
    await sync_mysql(data)
    sync_qdrant(data)
    
    print("\n" + "="*60)
    print("完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
