#!/usr/bin/env python3
"""
翻译剩余的 correct_steps_zh

使用 Ollama 将 correct_steps_en 翻译为中文
"""

import json
import sys
import os
import time
from ollama import Client
from neo4j import GraphDatabase

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("翻译剩余的 correct_steps_zh")
print("=" * 80)

# 连接 Neo4j
NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'your_password')

print(f"\n连接 Neo4j: {NEO4J_URI}")

try:
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    driver.verify_connectivity()
    print("✅ Neo4j 连接成功")
except Exception as e:
    print(f"❌ Neo4j 连接失败: {e}")
    sys.exit(1)

# 查询缺失 correct_steps_zh 的动作
def get_exercises_need_translation(session):
    """获取需要翻译的动作"""
    query = """
    MATCH (e:Exercise)
    WHERE e.correct_steps_zh IS NULL OR size(e.correct_steps_zh) = 0
    RETURN e.id as id, 
           e.name_zh as name_zh, 
           e.name_en as name_en,
           e.correct_steps_en as correct_steps_en
    ORDER BY e.id
    """
    result = session.run(query)
    return [record.data() for record in result]

# 连接 Ollama（Docker环境中连接宿主机）
print("\n连接 Ollama...")
ollama_host = os.getenv('OLLAMA_HOST', 'http://host.docker.internal:11434')
print(f"Ollama 地址: {ollama_host}")

try:
    client = Client(host=ollama_host)
    # 测试连接
    client.list()
    print("✅ Ollama 连接成功")
except Exception as e:
    print(f"❌ Ollama 连接失败: {e}")
    print("\n请确保 Ollama 服务正在运行：")
    print("  Windows: 检查 Ollama 应用是否启动")
    print(f"  或访问: {ollama_host}")
    sys.exit(1)

def translate_steps(client, steps_en, name_zh):
    """使用 Ollama 翻译步骤"""
    if not steps_en or len(steps_en) == 0:
        return []
    
    # 提取步骤文本
    if isinstance(steps_en[0], dict):
        steps_text = [step.get('text', '') for step in steps_en]
    else:
        steps_text = steps_en
    
    # 构建提示词
    prompt = f"""请将以下健身动作"{name_zh}"的英文步骤翻译成中文。

要求：
1. 保持专业健身术语
2. 翻译准确、流畅
3. 每行一个步骤
4. 不要添加编号
5. 不要添加任何额外说明

英文步骤：
{chr(10).join(steps_text)}

中文步骤："""
    
    try:
        response = client.generate(
            model='qwen3:8b',
            prompt=prompt,
            options={
                'temperature': 0.3,
                'num_predict': 300,
            }
        )
        
        # 解析响应
        translated_text = response['response'].strip()
        
        # 分割成步骤（按换行符）
        steps_zh = [line.strip() for line in translated_text.split('\n') if line.strip()]
        
        # 清理可能的编号
        import re
        steps_zh = [re.sub(r'^[1-9]\d*[\.。、]\s*', '', step) for step in steps_zh]
        
        return steps_zh
    
    except Exception as e:
        print(f"  ❌ 翻译失败: {e}")
        return []

def update_exercise_steps(session, exercise_id, correct_steps_zh):
    """更新 Neo4j 中的步骤"""
    query = """
    MATCH (e:Exercise {id: $exercise_id})
    SET e.correct_steps_zh = $correct_steps_zh
    RETURN e.id as id, e.name_zh as name_zh
    """
    result = session.run(query, exercise_id=exercise_id, correct_steps_zh=correct_steps_zh)
    return result.single()

# 主流程
print("\n查询需要翻译的动作...")

with driver.session() as session:
    exercises_need_translation = get_exercises_need_translation(session)

print(f"找到 {len(exercises_need_translation)} 个需要翻译的动作")

if len(exercises_need_translation) == 0:
    print("\n✅ 所有动作都已有 correct_steps_zh！")
    driver.close()
    sys.exit(0)

# 显示前5个
print("\n前5个需要翻译的动作：")
for i, ex in enumerate(exercises_need_translation[:5], 1):
    print(f"  {i}. ID={ex['id']}, {ex['name_zh']}, 步骤数={len(ex['correct_steps_en'])}")

# 确认开始
print(f"\n准备翻译 {len(exercises_need_translation)} 个动作...")
print("预计时间: 约 2-3 分钟")
print("-" * 80)

# 开始翻译
stats = {
    "total": len(exercises_need_translation),
    "success": 0,
    "failed": 0,
    "skipped": 0,
}

start_time = time.time()

with driver.session() as session:
    for i, exercise in enumerate(exercises_need_translation, 1):
        ex_id = exercise['id']
        name_zh = exercise['name_zh']
        name_en = exercise['name_en']
        steps_en = exercise['correct_steps_en']
        
        print(f"\n[{i}/{len(exercises_need_translation)}] ID={ex_id}, {name_zh}")
        
        # 检查是否有英文步骤
        if not steps_en or len(steps_en) == 0:
            print(f"  ⏭️ 跳过（无英文步骤）")
            stats["skipped"] += 1
            continue
        
        # 翻译
        print(f"  🔄 翻译中... ({len(steps_en)} 个步骤)")
        steps_zh = translate_steps(client, steps_en, name_zh)
        
        if steps_zh and len(steps_zh) >= 2:
            # 更新数据库
            result = update_exercise_steps(session, ex_id, steps_zh)
            if result:
                print(f"  ✅ 成功！翻译了 {len(steps_zh)} 个步骤")
                print(f"     第一步: {steps_zh[0][:50]}...")
                stats["success"] += 1
            else:
                print(f"  ❌ 更新失败")
                stats["failed"] += 1
        else:
            print(f"  ❌ 翻译失败或步骤太少")
            stats["failed"] += 1
        
        # 短暂延迟，避免过载
        time.sleep(0.5)

driver.close()

# 输出结果
elapsed_time = time.time() - start_time

print("\n\n" + "=" * 80)
print("翻译完成")
print("=" * 80)

print(f"\n总动作数: {stats['total']}")
print(f"成功翻译: {stats['success']}")
print(f"翻译失败: {stats['failed']}")
print(f"跳过: {stats['skipped']}")
print(f"耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")

if stats['success'] > 0:
    print(f"\n平均每个动作: {elapsed_time/stats['success']:.1f} 秒")

print("\n✅ 所有翻译任务完成！")
print("\n当前数据状态：")
print("  - correct_steps_zh: 应该接近 100% 完整")
print("  - correct_steps_en: 100% 完整")
print("  - description_zh: 已清空（等待重新爬取）")
print("  - description_en: 已清空（等待重新爬取）")

print("\n" + "=" * 80)
