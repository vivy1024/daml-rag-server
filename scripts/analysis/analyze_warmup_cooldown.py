"""
分析热身和放松动作数据
从运动学教授和专业教练的视角筛选动作
"""
from neo4j import GraphDatabase
import json

driver = GraphDatabase.driver('bolt://fitness_neo4j:7687', auth=('neo4j', 'build_body_2024'))

def analyze_exercises():
    with driver.session() as session:
        # 1. 查询恢复类动作
        print("=" * 80)
        print("恢复类动作 (Recovery Exercises)")
        print("=" * 80)
        result = session.run("""
            MATCH (e:Exercise)
            WHERE '恢复' IN e.equipment_zh
            RETURN e.id as id, e.name_zh as name, e.name as name_en,
                   e.primary_muscle_zh as muscle, 
                   e.secondary_muscles_zh as secondary,
                   e.force as force, e.kinetic_chain as kinetic
            ORDER BY e.primary_muscle_zh, e.name_zh
        """)
        recovery_exercises = []
        for record in result:
            recovery_exercises.append({
                "id": record["id"],
                "name": record["name"],
                "name_en": record["name_en"],
                "muscle": record["muscle"],
                "secondary": record["secondary"],
                "force": record["force"],
                "kinetic": record["kinetic"]
            })
            print(f"ID:{record['id']:4d} | {record['name'][:30]:30s} | 主肌:{record['muscle']}")
        print(f"\n恢复类动作总数: {len(recovery_exercises)}")
        
        # 2. 查询拉伸类动作
        print("\n" + "=" * 80)
        print("拉伸类动作 (Stretching Exercises)")
        print("=" * 80)
        result = session.run("""
            MATCH (e:Exercise)
            WHERE '拉伸' IN e.equipment_zh
            RETURN e.id as id, e.name_zh as name, e.name as name_en,
                   e.primary_muscle_zh as muscle,
                   e.secondary_muscles_zh as secondary,
                   e.force as force
            ORDER BY e.primary_muscle_zh, e.name_zh
        """)
        stretch_exercises = []
        for record in result:
            stretch_exercises.append({
                "id": record["id"],
                "name": record["name"],
                "name_en": record["name_en"],
                "muscle": record["muscle"],
                "secondary": record["secondary"],
                "force": record["force"]
            })
            print(f"ID:{record['id']:4d} | {record['name'][:30]:30s} | 主肌:{record['muscle']}")
        print(f"\n拉伸类动作总数: {len(stretch_exercises)}")
        
        # 3. 查询瑜伽类动作
        print("\n" + "=" * 80)
        print("瑜伽类动作 (Yoga Exercises)")
        print("=" * 80)
        result = session.run("""
            MATCH (e:Exercise)
            WHERE '瑜伽' IN e.equipment_zh
            RETURN e.id as id, e.name_zh as name, e.name as name_en,
                   e.primary_muscle_zh as muscle,
                   e.secondary_muscles_zh as secondary,
                   e.force as force
            ORDER BY e.primary_muscle_zh, e.name_zh
        """)
        yoga_exercises = []
        for record in result:
            yoga_exercises.append({
                "id": record["id"],
                "name": record["name"],
                "name_en": record["name_en"],
                "muscle": record["muscle"],
                "secondary": record["secondary"],
                "force": record["force"]
            })
            print(f"ID:{record['id']:4d} | {record['name'][:30]:30s} | 主肌:{record['muscle']}")
        print(f"\n瑜伽类动作总数: {len(yoga_exercises)}")
        
        # 4. 查询有氧类动作（适合热身）
        print("\n" + "=" * 80)
        print("有氧类动作 (Cardio Exercises - 适合热身)")
        print("=" * 80)
        result = session.run("""
            MATCH (e:Exercise)
            WHERE '有氧训练' IN e.equipment_zh
            RETURN e.id as id, e.name_zh as name, e.name as name_en,
                   e.primary_muscle_zh as muscle,
                   e.secondary_muscles_zh as secondary,
                   e.force as force
            ORDER BY e.primary_muscle_zh, e.name_zh
        """)
        cardio_exercises = []
        for record in result:
            cardio_exercises.append({
                "id": record["id"],
                "name": record["name"],
                "name_en": record["name_en"],
                "muscle": record["muscle"],
                "secondary": record["secondary"],
                "force": record["force"]
            })
            print(f"ID:{record['id']:4d} | {record['name'][:30]:30s} | 主肌:{record['muscle']}")
        print(f"\n有氧类动作总数: {len(cardio_exercises)}")
        
        # 5. 查询徒手训练中的激活动作（适合热身）
        print("\n" + "=" * 80)
        print("徒手训练动作 - hold类型 (适合热身激活)")
        print("=" * 80)
        result = session.run("""
            MATCH (e:Exercise)
            WHERE '徒手训练' IN e.equipment_zh AND e.force = 'hold'
            RETURN e.id as id, e.name_zh as name, e.name as name_en,
                   e.primary_muscle_zh as muscle,
                   e.secondary_muscles_zh as secondary,
                   e.force as force
            ORDER BY e.primary_muscle_zh, e.name_zh
        """)
        hold_exercises = []
        for record in result:
            hold_exercises.append({
                "id": record["id"],
                "name": record["name"],
                "name_en": record["name_en"],
                "muscle": record["muscle"],
                "secondary": record["secondary"],
                "force": record["force"]
            })
            print(f"ID:{record['id']:4d} | {record['name'][:30]:30s} | 主肌:{record['muscle']}")
        print(f"\n徒手hold类动作总数: {len(hold_exercises)}")
        
        # 6. 按肌群分类统计
        print("\n" + "=" * 80)
        print("按主要肌群分类统计")
        print("=" * 80)
        result = session.run("""
            MATCH (e:Exercise)
            WHERE '恢复' IN e.equipment_zh OR '拉伸' IN e.equipment_zh OR '瑜伽' IN e.equipment_zh
            RETURN e.primary_muscle_zh as muscle, count(*) as count
            ORDER BY count DESC
        """)
        for record in result:
            print(f"{record['muscle']}: {record['count']}个动作")
        
        # 保存数据到JSON
        data = {
            "recovery": recovery_exercises,
            "stretch": stretch_exercises,
            "yoga": yoga_exercises,
            "cardio": cardio_exercises,
            "hold": hold_exercises
        }
        
        with open('/app/scripts/warmup_cooldown_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print("\n数据已保存到 warmup_cooldown_data.json")

if __name__ == "__main__":
    analyze_exercises()
    driver.close()
