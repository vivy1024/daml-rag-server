#!/usr/bin/env python3
"""
修复MySQL exercises表的difficulty_zh值
统一为：零基础、初级、中级、高级
"""

import asyncio
import os
import sys
sys.path.insert(0, '/app')

import aiomysql


async def main():
    print("="*60)
    print("修复MySQL difficulty_zh值")
    print("="*60)
    
    conn = await aiomysql.connect(
        host=os.getenv("MYSQL_HOST", "mysql"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        user=os.getenv("MYSQL_USER", "fitness_user"),
        password=os.getenv("MYSQL_PASSWORD", "fitness_password"),
        db=os.getenv("MYSQL_DATABASE", "fitness_app")
    )
    
    async with conn.cursor() as cursor:
        print("\n修复前分布:")
        await cursor.execute("""
            SELECT difficulty_zh, COUNT(*) as count 
            FROM exercises 
            GROUP BY difficulty_zh 
            ORDER BY count DESC
        """)
        for row in await cursor.fetchall():
            print(f"  {row[0] or 'NULL'}: {row[1]}")
        
        mappings = [
            ("新手", "零基础"),
            ("初学者", "初级"),
        ]
        
        print("\n执行修复:")
        for old_val, new_val in mappings:
            await cursor.execute(
                "UPDATE exercises SET difficulty_zh = %s WHERE difficulty_zh = %s",
                (new_val, old_val)
            )
            affected = cursor.rowcount
            print(f"  {old_val} -> {new_val}: {affected}行")
        
        await conn.commit()
        
        print("\n修复后分布:")
        await cursor.execute("""
            SELECT difficulty_zh, COUNT(*) as count 
            FROM exercises 
            GROUP BY difficulty_zh 
            ORDER BY count DESC
        """)
        for row in await cursor.fetchall():
            print(f"  {row[0] or 'NULL'}: {row[1]}")
    
    conn.close()
    print("\n完成!")


if __name__ == "__main__":
    asyncio.run(main())
