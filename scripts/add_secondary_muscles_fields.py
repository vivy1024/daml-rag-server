#!/usr/bin/env python3
"""
添加muscles_secondary字段到MySQL和Qdrant
从muscles_tree中提取secondary肌群数据
"""

import asyncio
import os
import sys
import json
from pathlib import Path
sys.path.insert(0, '/app')

import aiomysql
from qdrant_client import QdrantClient


def extract_secondary_muscles_from_tree(muscles_tree: list, primary_zh: list, primary_en: list) -> tuple:
    """从muscles_tree中提取次要肌群（排除主要肌群）"""
    if not muscles_tree:
        return None, None
    
    secondary_zh = []
    secondary_en = []
    
    for muscle in muscles_tree:
        name_zh = muscle.get("name_zh", "")
        name_en = muscle.get("name", "")
        
        # 如果不在主要肌群中，则为次要肌群
        if name_zh and name_zh not in primary_zh:
            secondary_zh.append(name_zh)
        if name_en and name_en not in primary_en:
            secondary_en.append(name_en)
    
    return (secondary_zh if secondary_zh else None, 
            secondary_en if secondary_en else None)


async def add_mysql_columns():
    """MySQL添加muscles_secondary_zh和muscles_secondary_en字段"""
    print("\n" + "="*60)
    print("MySQL: 添加muscles_secondary字段")
    print("="*60)
    
    conn = await aiomysql.connect(
        host=os.getenv("MYSQL_HOST", "fitness_mysql"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "fitness_user"),
        password=os.getenv("MYSQL_PASSWORD", "fitness_pass"),
        db=os.getenv("MYSQL_DATABASE", "fitness_app")
    )
    
    async with conn.cursor() as cursor:
        # 检查字段是否存在
        await cursor.execute("DESCRIBE exercises")
        columns = [col[0] for col in await cursor.fetchall()]
        
        # 添加muscles_secondary_zh
        if "muscles_secondary_zh" not in columns:
            print("添加 muscles_secondary_zh 字段...")
            await cursor.execute("""
                ALTER TABLE exercises 
                ADD COLUMN muscles_secondary_zh JSON NULL 
                COMMENT '次要肌群（中文）'
                AFTER muscles_primary_zh
            """)
            print("  已添加 muscles_secondary_zh")
        else:
            print("  muscles_secondary_zh 已存在")
        
        # 添加muscles_secondary_en
        if "muscles_secondary_en" not in columns:
            print("添加 muscles_secondary_en 字段...")
            await cursor.execute("""
                ALTER TABLE exercises 
                ADD COLUMN muscles_secondary_en JSON NULL 
                COMMENT '次要肌群（英文）'
                AFTER muscles_secondary_zh
            """)
            print("  已添加 muscles_secondary_en")
        else:
            print("  muscles_secondary_en 已存在")
        
        await conn.commit()
        
        # 从muscles_tree提取次要肌群数据
        print("\n从muscles_tree提取次要肌群...")
        
        # 获取所有exercise的muscles_tree和primary数据
        await cursor.execute("""
            SELECT id, muscles_tree, muscles_primary_zh, muscles_primary_en 
            FROM exercises
        """)
        rows = await cursor.fetchall()
        
        updated = 0
        for row in rows:
            eid, muscles_tree_json, primary_zh_json, primary_en_json = row
            
            # 解析JSON
            try:
                muscles_tree = json.loads(muscles_tree_json) if muscles_tree_json else []
                primary_zh = json.loads(primary_zh_json) if primary_zh_json else []
                primary_en = json.loads(primary_en_json) if primary_en_json else []
            except (json.JSONDecodeError, TypeError):
                continue
            
            # 提取次要肌群
            sec_zh, sec_en = extract_secondary_muscles_from_tree(
                muscles_tree, primary_zh, primary_en
            )
            
            if sec_zh or sec_en:
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
        print(f"  已更新 {updated} 条记录")
        
        # 验证
        await cursor.execute("""
            SELECT COUNT(*) FROM exercises 
            WHERE muscles_secondary_zh IS NOT NULL
        """)
        count = (await cursor.fetchone())[0]
        print(f"\n验证: {count} 条记录有 muscles_secondary_zh")
        
        # 显示示例
        await cursor.execute("""
            SELECT id, name_zh, muscles_primary_zh, muscles_secondary_zh 
            FROM exercises 
            WHERE muscles_secondary_zh IS NOT NULL 
            LIMIT 3
        """)
        samples = await cursor.fetchall()
        print("\n示例数据:")
        for s in samples:
            print(f"  ID {s[0]}: {s[1]}")
            print(f"    主要: {s[2]}")
            print(f"    次要: {s[3]}")
    
    conn.close()


def add_qdrant_secondary_en():
    """Qdrant添加muscles_secondary_en字段（从muscles_tree提取）"""
    print("\n" + "="*60)
    print("Qdrant: 添加muscles_secondary_en字段")
    print("="*60)
    
    client = QdrantClient(host="qdrant", port=6333)
    
    # 获取集合信息
    collection_info = client.get_collection("fitness_exercises_v2")
    total_points = collection_info.points_count
    print(f"总向量数: {total_points}")
    
    # 分批处理
    batch_size = 100
    offset = None
    updated_count = 0
    
    while True:
        results, next_offset = client.scroll(
            collection_name="fitness_exercises_v2",
            limit=batch_size,
            offset=offset,
            with_payload=True,
            with_vectors=False
        )
        
        if not results:
            break
        
        for point in results:
            payload = point.payload
            
            # 获取muscles_tree和primary数据
            muscles_tree = payload.get("muscles_tree", [])
            primary_zh = payload.get("muscles_primary_zh", [])
            primary_en = payload.get("muscles_primary_en", [])
            
            # 如果已有muscles_secondary_en且不为空，跳过
            if payload.get("muscles_secondary_en"):
                continue
            
            # 从muscles_tree提取次要肌群
            sec_zh, sec_en = extract_secondary_muscles_from_tree(
                muscles_tree, primary_zh, primary_en
            )
            
            if sec_en:
                update_payload = {"muscles_secondary_en": sec_en}
                # 同时更新中文（如果没有）
                if sec_zh and not payload.get("muscles_secondary_zh"):
                    update_payload["muscles_secondary_zh"] = sec_zh
                
                client.set_payload(
                    collection_name="fitness_exercises_v2",
                    payload=update_payload,
                    points=[point.id]
                )
                updated_count += 1
        
        if updated_count > 0 and updated_count % 100 == 0:
            print(f"  已更新 {updated_count} 个点")
        
        offset = next_offset
        if offset is None:
            break
    
    print(f"完成！共更新 {updated_count} 个点")
    
    # 验证
    print("\n验证结果:")
    results, _ = client.scroll(
        collection_name="fitness_exercises_v2",
        limit=100,
        with_payload=True
    )
    has_en = sum(1 for r in results if r.payload.get("muscles_secondary_en"))
    has_zh = sum(1 for r in results if r.payload.get("muscles_secondary_zh"))
    print(f"  前100个中有 muscles_secondary_en: {has_en}个")
    print(f"  前100个中有 muscles_secondary_zh: {has_zh}个")
    
    # 显示示例
    print("\n示例数据:")
    for r in results[:3]:
        if r.payload.get("muscles_secondary_en"):
            print(f"  ID {r.payload.get('id')}: {r.payload.get('name_zh')}")
            print(f"    主要: {r.payload.get('muscles_primary_en')}")
            print(f"    次要: {r.payload.get('muscles_secondary_en')}")


async def main():
    print("="*60)
    print("添加muscles_secondary字段")
    print("="*60)
    
    # MySQL
    await add_mysql_columns()
    
    # Qdrant
    add_qdrant_secondary_en()
    
    print("\n" + "="*60)
    print("完成！")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
