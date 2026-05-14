#!/usr/bin/env python3
"""
估算数据净化所需时间

基于 Ollama Qwen3 8B 的实际性能进行估算
"""

import json
import sys
import os
import time
from ollama import Client

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

print("=" * 80)
print("数据净化时间估算")
print("=" * 80)

# 读取数据
db_file = 'data/enhanced_perfect_exercises_dataset.json'
print(f"\n读取数据库文件: {db_file}")

with open(db_file, 'r', encoding='utf-8') as f:
    db_data = json.load(f)

if isinstance(db_data, dict):
    if 'enhanced_perfect_exercises' in db_data:
        exercises = db_data['enhanced_perfect_exercises']
    elif 'exercises' in db_data:
        exercises = db_data['exercises']
else:
    exercises = db_data

total_exercises = len(exercises)
exercises_need_steps_zh = sum(1 for e in exercises if not e.get('correct_steps_zh') or len(e.get('correct_steps_zh', [])) == 0)
exercises_need_desc_en = total_exercises  # 所有动作都需要重新生成 description_en

print(f"\n总动作数: {total_exercises}")
print(f"需要补充 correct_steps_zh: {exercises_need_steps_zh} 个")
print(f"需要生成 description_en: {exercises_need_desc_en} 个")

# 测试 Ollama 性能
print("\n\n【性能测试】")
print("-" * 80)

try:
    client = Client(host='http://localhost:11434')
    
    # 测试1: 生成中文步骤（翻译）
    print("\n测试1: 翻译英文步骤为中文")
    test_steps_en = [
        "Hold the dumbbells with a neutral grip (thumbs facing the ceiling).",
        "Slowly lift the dumbbell up to chest height",
        "Return to starting position and repeat."
    ]
    
    prompt_translate = f"""请将以下英文动作步骤翻译成中文，保持专业性和准确性。
只返回翻译后的步骤，每行一个步骤，不要添加编号或其他内容。

英文步骤：
{chr(10).join(test_steps_en)}

中文步骤："""
    
    start_time = time.time()
    response = client.generate(
        model='qwen2.5:3b',
        prompt=prompt_translate,
        options={
            'temperature': 0.3,
            'num_predict': 200,
        }
    )
    translate_time = time.time() - start_time
    
    print(f"  耗时: {translate_time:.2f} 秒")
    print(f"  生成内容: {response['response'][:100]}...")
    
    # 测试2: 生成英文描述
    print("\n测试2: 生成英文动作描述")
    test_exercise = {
        "name_zh": "哑铃锤式弯举",
        "name_en": "Dumbbell Hammer Curl",
        "primary_muscle_zh": "肱二头肌短头",
        "equipment_zh": "哑铃",
        "difficulty": "新手",
        "mechanic": "单关节动作",
    }
    
    prompt_desc = f"""请为以下健身动作生成一段专业的英文描述（description），约50-80词。

动作信息：
- 名称: {test_exercise['name_en']} ({test_exercise['name_zh']})
- 目标肌肉: {test_exercise['primary_muscle_zh']}
- 器械: {test_exercise['equipment_zh']}
- 难度: {test_exercise['difficulty']}
- 类型: {test_exercise['mechanic']}

要求：
1. 描述动作的特点和目标
2. 说明适合人群
3. 提及主要训练效果
4. 使用专业健身术语
5. 不要包含具体步骤

英文描述："""
    
    start_time = time.time()
    response = client.generate(
        model='qwen2.5:3b',
        prompt=prompt_desc,
        options={
            'temperature': 0.7,
            'num_predict': 150,
        }
    )
    desc_time = time.time() - start_time
    
    print(f"  耗时: {desc_time:.2f} 秒")
    print(f"  生成内容: {response['response'][:100]}...")
    
    # 计算总时间
    print("\n\n【时间估算】")
    print("=" * 80)
    
    # 方案1: 逐个处理
    print("\n方案1: 逐个处理（串行）")
    total_time_serial = (exercises_need_steps_zh * translate_time + 
                         exercises_need_desc_en * desc_time)
    print(f"  补充 correct_steps_zh: {exercises_need_steps_zh} × {translate_time:.2f}秒 = {exercises_need_steps_zh * translate_time / 60:.1f} 分钟")
    print(f"  生成 description_en: {exercises_need_desc_en} × {desc_time:.2f}秒 = {exercises_need_desc_en * desc_time / 60:.1f} 分钟")
    print(f"  总计: {total_time_serial / 60:.1f} 分钟 ({total_time_serial / 3600:.1f} 小时)")
    
    # 方案2: 批量处理（10个一批）
    print("\n方案2: 批量处理（10个一批）")
    batch_size = 10
    batch_overhead = 1.2  # 批量处理的额外开销
    total_time_batch = ((exercises_need_steps_zh / batch_size * translate_time * batch_overhead) + 
                        (exercises_need_desc_en / batch_size * desc_time * batch_overhead))
    print(f"  补充 correct_steps_zh: {exercises_need_steps_zh / batch_size:.0f} 批 × {translate_time * batch_overhead:.2f}秒 = {exercises_need_steps_zh / batch_size * translate_time * batch_overhead / 60:.1f} 分钟")
    print(f"  生成 description_en: {exercises_need_desc_en / batch_size:.0f} 批 × {desc_time * batch_overhead:.2f}秒 = {exercises_need_desc_en / batch_size * desc_time * batch_overhead / 60:.1f} 分钟")
    print(f"  总计: {total_time_batch / 60:.1f} 分钟 ({total_time_batch / 3600:.1f} 小时)")
    
    # 方案3: 仅处理关键字段
    print("\n方案3: 仅补充 correct_steps_zh（保留现有 description）")
    total_time_minimal = exercises_need_steps_zh * translate_time
    print(f"  补充 correct_steps_zh: {exercises_need_steps_zh} × {translate_time:.2f}秒 = {total_time_minimal / 60:.1f} 分钟 ({total_time_minimal / 3600:.1f} 小时)")
    
    print("\n\n【建议】")
    print("=" * 80)
    
    print("\n💡 推荐方案：")
    if total_time_batch / 3600 < 2:
        print(f"  ✅ 方案2（批量处理）- 约 {total_time_batch / 3600:.1f} 小时，可接受")
    elif total_time_minimal / 3600 < 1:
        print(f"  ✅ 方案3（仅补充步骤）- 约 {total_time_minimal / 3600:.1f} 小时，最快")
    else:
        print(f"  ⚠️ 所有方案都需要较长时间，建议分批处理或使用更快的模型")
    
    print("\n📊 性能优化建议：")
    print("  1. 使用批量处理减少API调用次数")
    print("  2. 使用更小的模型（如 qwen2.5:1.5b）提升速度")
    print("  3. 分批处理，每次处理100-200个动作")
    print("  4. 考虑使用API服务（如OpenAI）提升速度")
    print("  5. 仅处理关键缺失字段，保留现有数据")
    
    print("\n🎯 实际建议：")
    print("  1. 优先补充 correct_steps_zh（957个，约1-2小时）")
    print("  2. description_en 可以保持现状（虽然是步骤，但至少有内容）")
    print("  3. 或者仅为关键动作（如深蹲、硬拉等）生成高质量描述")
    print("  4. 分批执行，避免一次性处理所有数据")

except Exception as e:
    print(f"\n❌ 错误: {e}")
    print("\n无法连接到 Ollama 服务，使用理论估算：")
    print(f"  假设每个翻译需要 3-5 秒")
    print(f"  假设每个描述生成需要 5-8 秒")
    print(f"  补充 correct_steps_zh: {exercises_need_steps_zh} × 4秒 = {exercises_need_steps_zh * 4 / 60:.1f} 分钟")
    print(f"  生成 description_en: {exercises_need_desc_en} × 6秒 = {exercises_need_desc_en * 6 / 60:.1f} 分钟")
    print(f"  总计: {(exercises_need_steps_zh * 4 + exercises_need_desc_en * 6) / 3600:.1f} 小时")

print("\n" + "=" * 80)
print("估算完成")
print("=" * 80)
