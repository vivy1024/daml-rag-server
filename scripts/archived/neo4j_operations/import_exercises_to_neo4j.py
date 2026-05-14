#!/usr/bin/env python3
"""
导入Exercise数据到Neo4j图数据库

读取enhanced_perfect_exercises_dataset.json，正确展开嵌套对象，创建完整的Exercise节点。

Author: 薛小川
Created: 2025-12-14
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any
from neo4j import GraphDatabase

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ExerciseNeo4jImporter:
    """Exercise数据Neo4j导入器"""
    
    def __init__(
        self,
        data_file: str,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "your_password"
    ):
        """
        初始化
        
        Args:
            data_file: Exercise数据文件路径
            neo4j_uri: Neo4j连接URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        self.data_file = Path(data_file)
        
        # 连接Neo4j
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        print(f"✅ 连接到Neo4j: {neo4j_uri}")
    
    def close(self):
        """关闭连接"""
        self.driver.close()
    
    def load_exercises(self) -> List[Dict[str, Any]]:
        """加载Exercise数据"""
        print(f"\n📥 加载数据文件: {self.data_file}")
        
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        exercises = data.get('enhanced_perfect_exercises', [])
        print(f"✅ 加载了 {len(exercises)} 个Exercise")
        
        return exercises
    
    def flatten_exercise_data(self, exercise: Dict[str, Any]) -> Dict[str, Any]:
        """
        展开Exercise数据的嵌套对象
        
        将training_parameters, safety_guidelines, nutrition_guidance展开为平面字段
        """
        flattened = {}
        
        # 基础字段
        flattened['id'] = exercise.get('id')
        flattened['name_zh'] = exercise.get('name_zh', '')
        flattened['name_en'] = exercise.get('name_en', '')
        flattened['description_zh'] = exercise.get('description_zh_professional', '') or exercise.get('description_zh', '')
        flattened['description_en'] = exercise.get('description_en', '')
        flattened['primary_muscle_zh'] = exercise.get('primary_muscle_zh', '')
        flattened['primary_muscle_en'] = exercise.get('primary_muscle_en', '')
        
        # 肌肉群信息 - 直接使用文件系统中的 all_muscles_zh 字段
        all_muscles_zh = exercise.get('all_muscles_zh', [])
        flattened['all_muscles_zh'] = all_muscles_zh if isinstance(all_muscles_zh, list) else []
        
        # 新增肌肉字段 (v2)
        all_muscles_en = exercise.get('all_muscles_en', [])
        flattened['all_muscles_en'] = all_muscles_en if isinstance(all_muscles_en, list) else []
        
        # muscles_tree - 存储为JSON字符串（Neo4j不支持嵌套对象数组）
        muscles_tree = exercise.get('muscles_tree', [])
        flattened['muscles_tree'] = json.dumps(muscles_tree, ensure_ascii=False) if muscles_tree else '[]'
        
        # muscles_primary_tree - 存储为JSON字符串
        muscles_primary_tree = exercise.get('muscles_primary_tree', [])
        flattened['muscles_primary_tree'] = json.dumps(muscles_primary_tree, ensure_ascii=False) if muscles_primary_tree else '[]'
        
        # 器械信息
        equipment_zh = exercise.get('equipment_zh', [])
        flattened['equipment_zh'] = equipment_zh if isinstance(equipment_zh, list) else [equipment_zh] if equipment_zh else []
        
        equipment_en = exercise.get('equipment_en', [])
        flattened['equipment_en'] = equipment_en if isinstance(equipment_en, list) else [equipment_en] if equipment_en else []
        
        # 基础属性
        flattened['difficulty'] = exercise.get('difficulty', '中级')
        
        # force和mechanic可能是字典，提取name字段
        force = exercise.get('force', '')
        flattened['force'] = force.get('name', '') if isinstance(force, dict) else (force if force else '')
        
        mechanic = exercise.get('mechanic', '')
        flattened['mechanic'] = mechanic.get('name', '') if isinstance(mechanic, dict) else (mechanic if mechanic else '')
        
        flattened['grips'] = exercise.get('grips', []) if isinstance(exercise.get('grips'), list) else []
        
        # 动作步骤 - 处理可能的字典列表
        correct_steps_zh = exercise.get('correct_steps_zh', [])
        if isinstance(correct_steps_zh, list):
            # 如果是字典列表，提取text字段
            if correct_steps_zh and isinstance(correct_steps_zh[0], dict):
                flattened['correct_steps_zh'] = [step.get('text', '') if isinstance(step, dict) else str(step) for step in correct_steps_zh]
            else:
                flattened['correct_steps_zh'] = correct_steps_zh
        else:
            flattened['correct_steps_zh'] = []
        
        # 处理correct_steps_en - 同样处理字典列表
        correct_steps_en = exercise.get('correct_steps_en', [])
        if isinstance(correct_steps_en, list):
            # 如果是字典列表，提取text字段
            if correct_steps_en and isinstance(correct_steps_en[0], dict):
                flattened['correct_steps_en'] = [step.get('text', '') if isinstance(step, dict) else str(step) for step in correct_steps_en]
            else:
                flattened['correct_steps_en'] = correct_steps_en
        else:
            flattened['correct_steps_en'] = []
        if isinstance(correct_steps_en, list):
            # 如果是字典列表，提取text字段
            if correct_steps_en and isinstance(correct_steps_en[0], dict):
                flattened['correct_steps_en'] = [step.get('text', '') for step in correct_steps_en]
            else:
                flattened['correct_steps_en'] = correct_steps_en
        else:
            flattened['correct_steps_en'] = []
        
        # 展开training_parameters
        training_params = exercise.get('training_parameters', {})
        if isinstance(training_params, dict):
            flattened['rep_range'] = training_params.get('rep_range', '')
            flattened['set_range'] = training_params.get('set_range', '')
            flattened['rest_period'] = training_params.get('rest_period', '')
            flattened['intensity_percentage'] = training_params.get('intensity_percentage', '')
            flattened['frequency'] = training_params.get('frequency', '')
            flattened['progression'] = training_params.get('progression', '')
            
            technique_focus = training_params.get('technique_focus', [])
            flattened['technique_focus'] = technique_focus if isinstance(technique_focus, list) else []
        
        # 展开safety_guidelines
        safety = exercise.get('safety_guidelines', {})
        if isinstance(safety, dict):
            flattened['safety_level'] = safety.get('risk_level', 'MEDIUM_RISK')
            
            pre_check = safety.get('pre_workout_check', [])
            flattened['safety_pre_check'] = pre_check if isinstance(pre_check, list) else []
            
            during = safety.get('during_workout', [])
            flattened['safety_during'] = during if isinstance(during, list) else []
            
            warning = safety.get('warning_signs', [])
            flattened['safety_warning_signs'] = warning if isinstance(warning, list) else []
            
            equipment_risks = safety.get('equipment_risks', [])
            flattened['equipment_risks'] = equipment_risks if isinstance(equipment_risks, list) else []
        
        # 展开nutrition_guidance
        nutrition = exercise.get('nutrition_guidance', {})
        if isinstance(nutrition, dict):
            key_nutrients = nutrition.get('key_nutrients', [])
            flattened['key_nutrients'] = key_nutrients if isinstance(key_nutrients, list) else []
            
            recommended_foods = nutrition.get('recommended_foods', [])
            flattened['recommended_foods'] = recommended_foods if isinstance(recommended_foods, list) else []
            
            flattened['nutrition_timing'] = nutrition.get('timing_advice', '')
            flattened['target_muscle_nutrition'] = nutrition.get('target_muscle', '')
            
            daily_req = nutrition.get('daily_requirements', {})
            if isinstance(daily_req, dict):
                flattened['daily_protein'] = daily_req.get('protein', '')
                flattened['daily_water'] = daily_req.get('water', '')
                flattened['daily_rest'] = daily_req.get('rest', '')
        
        # 元数据
        enhancement_meta = exercise.get('enhancement_metadata', {})
        if isinstance(enhancement_meta, dict):
            flattened['data_source'] = enhancement_meta.get('source', 'enhanced_perfect_exercises')
            flattened['enhancement_version'] = enhancement_meta.get('version', '')
        
        return flattened
    
    def create_constraints_and_indexes(self):
        """创建约束和索引"""
        print("\n🔧 创建约束和索引...")
        
        with self.driver.session() as session:
            # 创建唯一约束
            try:
                session.run("""
                    CREATE CONSTRAINT exercise_id IF NOT EXISTS 
                    FOR (e:Exercise) REQUIRE e.id IS UNIQUE
                """)
                print("✅ 创建Exercise.id唯一约束")
            except Exception as e:
                print(f"⚠️  约束已存在或创建失败: {e}")
            
            # 创建索引
            indexes = [
                "CREATE INDEX exercise_name_zh IF NOT EXISTS FOR (e:Exercise) ON (e.name_zh)",
                "CREATE INDEX exercise_name_en IF NOT EXISTS FOR (e:Exercise) ON (e.name_en)",
                "CREATE INDEX exercise_difficulty IF NOT EXISTS FOR (e:Exercise) ON (e.difficulty)",
                "CREATE INDEX exercise_primary_muscle IF NOT EXISTS FOR (e:Exercise) ON (e.primary_muscle_zh)"
            ]
            
            for index_query in indexes:
                try:
                    session.run(index_query)
                except Exception as e:
                    print(f"⚠️  索引创建警告: {e}")
            
            print(f"✅ 创建索引: {len(indexes)} 个")
    
    def delete_existing_exercises(self, force: bool = False):
        """删除现有的Exercise节点"""
        print("\n🗑️  删除现有Exercise节点...")
        
        with self.driver.session() as session:
            # 统计现有节点
            result = session.run("MATCH (e:Exercise) RETURN count(e) as count")
            count = result.single()["count"]
            
            if count > 0:
                print(f"⚠️  发现 {count} 个现有Exercise节点")
                
                if force:
                    print("🔄 强制删除模式，自动删除现有节点")
                    response = 'y'
                else:
                    response = input("是否删除并重新导入？(y/n): ")
                
                if response.lower() == 'y':
                    # 删除Exercise节点及其关系
                    session.run("MATCH (e:Exercise) DETACH DELETE e")
                    print(f"✅ 已删除 {count} 个Exercise节点")
                else:
                    print("❌ 取消导入")
                    sys.exit(0)
            else:
                print("✅ 没有现有Exercise节点")
    
    def import_exercises(self, exercises: List[Dict[str, Any]]):
        """导入Exercise节点"""
        print(f"\n📥 开始导入 {len(exercises)} 个Exercise节点...")
        
        success_count = 0
        error_count = 0
        
        with self.driver.session() as session:
            for i, exercise in enumerate(exercises, 1):
                try:
                    # 展开数据
                    flattened = self.flatten_exercise_data(exercise)
                    
                    # 创建Exercise节点
                    cypher = """
                    CREATE (e:Exercise {
                        id: $id,
                        name_zh: $name_zh,
                        name_en: $name_en,
                        description_zh: $description_zh,
                        description_en: $description_en,
                        primary_muscle_zh: $primary_muscle_zh,
                        primary_muscle_en: $primary_muscle_en,
                        all_muscles_zh: $all_muscles_zh,
                        all_muscles_en: $all_muscles_en,
                        muscles_tree: $muscles_tree,
                        muscles_primary_tree: $muscles_primary_tree,
                        equipment_zh: $equipment_zh,
                        equipment_en: $equipment_en,
                        difficulty: $difficulty,
                        force: $force,
                        mechanic: $mechanic,
                        grips: $grips,
                        correct_steps_zh: $correct_steps_zh,
                        correct_steps_en: $correct_steps_en,
                        rep_range: $rep_range,
                        set_range: $set_range,
                        rest_period: $rest_period,
                        intensity_percentage: $intensity_percentage,
                        frequency: $frequency,
                        progression: $progression,
                        technique_focus: $technique_focus,
                        safety_level: $safety_level,
                        safety_pre_check: $safety_pre_check,
                        safety_during: $safety_during,
                        safety_warning_signs: $safety_warning_signs,
                        equipment_risks: $equipment_risks,
                        key_nutrients: $key_nutrients,
                        recommended_foods: $recommended_foods,
                        nutrition_timing: $nutrition_timing,
                        target_muscle_nutrition: $target_muscle_nutrition,
                        daily_protein: $daily_protein,
                        daily_water: $daily_water,
                        daily_rest: $daily_rest,
                        data_source: $data_source,
                        enhancement_version: $enhancement_version,
                        created_at: datetime(),
                        updated_at: datetime()
                    })
                    """
                    
                    session.run(cypher, flattened)
                    success_count += 1
                    
                    if i % 100 == 0:
                        print(f"  进度: {i}/{len(exercises)} ({i*100//len(exercises)}%)")
                
                except Exception as e:
                    error_count += 1
                    print(f"❌ 导入失败 (ID: {exercise.get('id')}): {e}")
        
        print(f"\n✅ 导入完成: 成功 {success_count} 个, 失败 {error_count} 个")
    
    def verify_import(self):
        """验证导入结果"""
        print("\n📊 验证导入结果...")
        
        with self.driver.session() as session:
            # 统计总数
            result = session.run("MATCH (e:Exercise) RETURN count(e) as count")
            total = result.single()["count"]
            print(f"  总Exercise节点: {total}")
            
            # 统计字段完整度
            field_checks = [
                ("difficulty", "e.difficulty IS NOT NULL AND e.difficulty <> ''"),
                ("safety_level", "e.safety_level IS NOT NULL AND e.safety_level <> ''"),
                ("rep_range", "e.rep_range IS NOT NULL AND e.rep_range <> ''"),
                ("set_range", "e.set_range IS NOT NULL AND e.set_range <> ''"),
                ("equipment_zh", "size(e.equipment_zh) > 0"),
                ("key_nutrients", "size(e.key_nutrients) > 0")
            ]
            
            print("\n字段完整度:")
            for field_name, condition in field_checks:
                result = session.run(f"""
                    MATCH (e:Exercise)
                    WHERE {condition}
                    RETURN count(e) as count
                """)
                count = result.single()["count"]
                percentage = (count / total * 100) if total > 0 else 0
                print(f"  - {field_name}: {count}/{total} ({percentage:.1f}%)")
            
            # 测试查询
            print("\n🔍 测试查询: 查找胸部训练动作")
            result = session.run("""
                MATCH (e:Exercise)
                WHERE e.primary_muscle_zh CONTAINS '胸'
                RETURN e.name_zh as name, e.difficulty as difficulty, e.safety_level as safety
                LIMIT 5
            """)
            
            for record in result:
                print(f"  - {record['name']} (难度: {record['difficulty']}, 安全: {record['safety']})")
    
    def run(self, force: bool = False):
        """执行完整导入流程"""
        print("=" * 60)
        print("🚀 开始导入Exercise数据到Neo4j")
        print("=" * 60)
        
        try:
            # 1. 加载数据
            exercises = self.load_exercises()
            
            # 2. 创建约束和索引
            self.create_constraints_and_indexes()
            
            # 3. 删除现有数据
            self.delete_existing_exercises(force=force)
            
            # 4. 导入Exercise节点
            self.import_exercises(exercises)
            
            # 5. 验证导入
            self.verify_import()
            
            print("\n" + "=" * 60)
            print("✅ Exercise数据导入Neo4j完成！")
            print("=" * 60)
            
        except Exception as e:
            print(f"\n❌ 导入失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.close()


def main():
    """主函数"""
    import argparse
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='导入Exercise数据到Neo4j')
    parser.add_argument('--force', '-f', action='store_true', 
                       help='强制删除现有数据，不需要确认')
    args = parser.parse_args()
    
    # 配置路径 - 项目根目录
    project_root = Path(__file__).parent.parent.parent
    
    # 尝试多个可能的路径
    possible_paths = [
        project_root / "data" / "enhanced_perfect_exercises_dataset.json",  # Docker容器内路径 /app/data/
        Path("/app/data/enhanced_perfect_exercises_dataset.json"),  # Docker绝对路径
        project_root.parent / "perfect_enhanced_dataset" / "data" / "enhanced_perfect_exercises_dataset.json"  # 本地路径
    ]
    
    data_file = None
    for path in possible_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        print(f"❌ 数据文件不存在，尝试过的路径:")
        for path in possible_paths:
            print(f"  - {path}")
        return
    
    # 从环境变量读取Neo4j配置
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://fitness_neo4j:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'build_body_2024')
    
    # 执行导入
    importer = ExerciseNeo4jImporter(
        data_file=str(data_file),
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password
    )
    importer.run(force=args.force)


if __name__ == "__main__":
    main()
