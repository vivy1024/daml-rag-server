import asyncio
import os
from neo4j import AsyncGraphDatabase

async def check():
    password = os.getenv('NEO4J_PASSWORD', 'build_body_2024')
    driver = AsyncGraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', password))
    async with driver.session() as s:
        # 检查有carbohydrate字段的Food节点
        r = await s.run('MATCH (f:Food) WHERE f.carbohydrate IS NOT NULL RETURN count(f) as count')
        rec = await r.single()
        print(f'有carbohydrate字段的Food节点: {rec["count"]}')
        
        # 查看一些示例
        r = await s.run('MATCH (f:Food) WHERE f.carbohydrate IS NOT NULL AND f.glycemic_index IS NOT NULL RETURN f.name, f.carbohydrate, f.glycemic_index LIMIT 5')
        records = await r.data()
        print('\n有GI和碳水的示例:')
        for rec in records:
            print(f"  {rec['f.name']}: carbs={rec['f.carbohydrate']}, GI={rec['f.glycemic_index']}")
    
    await driver.close()

asyncio.run(check())
