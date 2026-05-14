import asyncio
import os
from neo4j import AsyncGraphDatabase

async def check():
    password = os.getenv('NEO4J_PASSWORD', 'build_body_2024')
    driver = AsyncGraphDatabase.driver('bolt://neo4j:7687', auth=('neo4j', password))
    async with driver.session() as s:
        r = await s.run('MATCH (f:Food) RETURN f LIMIT 1')
        rec = await r.single()
        print('Food节点字段:', list(rec['f'].keys()))
        print('\n完整数据:')
        for key, value in rec['f'].items():
            print(f"  {key}: {value}")
    
    await driver.close()

asyncio.run(check())
