#!/usr/bin/env python3
"""
增量更新Neo4j Exercise节点

功能：
1. 更新现有节点ID（使用临时属性避免冲突）
2. 添加新肌肉字段 (all_muscles_en, muscles_tree, muscles_primary_tree)
3. 创建新节点

Author: 薛小川
Created: 2026-01-05
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from neo4j import GraphDatabase

# 禁用代理
os.environ['NO_PROXY'] = 'localhost,127.0.0.1,fitness_neo4j'
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


class ExerciseIncrementalUpdater:
    """Exercise节点增量更新器"""
    
    def __init__(
        self,
        data_file: str,
        mapping_file: str,
        neo4j_uri: str = "bolt://fitness_neo4j:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "build_body_2024"
    ):
        """
        初始化
        
        Args:
            data_file: 增强数据集文件路径
            mapping_file: ID映射文件路径
            neo4j_uri: Neo4j连接URI
            neo4j_user: Neo4j用户名
            neo4j_password: Neo4j密码
        """
        self.data_file = Path(data_file)
        self.mapping_file = Path(mapping_file)
        
        # 连接Neo4j
        self.driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password)
        )
        
        print(f"✅ 连接到Neo4j: {neo4j_uri}")
        
        # 加载数据
        self.exercises = {}
        self.id_mapping = {}
        self.new_exercise_ids = []
        
    def close(self):
        """关闭连接"""
        self.driver.close()
    
    def load_data(self):
        """加载增强数据集和ID映射"""
        print(f"\n📥 加载数据文件...")
        
        # 加载增强数据集
        with open(self.data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        exercises_list = data.get('enhanced_perfect_exercises', [])
        self.exercises = {ex['id']: ex for ex in exercises_list}
        print(f"  ✅ 加载了 {len(self.exercises)} 个Exercise")
        
        # 加载ID映射
        with open(self.mapping_file, 'r', encoding='utf-8') as f:
            mapping_data = json.load(f)
        
        self.id_mapping = mapping_data.get('mapping', {})
        self.new_exercise_ids = mapping_data.get('new_fs_ids', [])
        
        print(f"  ✅ 加载了 {len(self.id_mapping)} 个ID映射")
        print(f"  ✅ 识别了 {len(self.new_exercise_ids)} 个新增动作")
    
    def get_current_neo4j_status(self) -> Dict[str, Any]:
        """获取当前Neo4j状态"""
        print(f"\n📊 检查Neo4j当前状态...")
        
        with self.driver.session() as session:
            # 统计Exercise节点数量
            result = session.run('MATCH (e:Exercise) RETURN count(e) as count')
            count = result.single()['count']
            
            # 查看ID范围
            result = session.run('MATCH (e:Exercise) RETURN min(e.id) as min_id, max(e.id) as max_id')
            record = result.single()
            
            # 检查新肌肉字段
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.all_muscles_en IS NOT NULL
                RETURN count(e) as count
            ''')
            with_muscles_en = result.single()['count']
            
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.muscles_tree IS NOT NULL
                RETURN count(e) as count
            ''')
            with_muscles_tree = result.single()['count']
            
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.muscles_primary_tree IS NOT NULL
                RETURN count(e) as count
            ''')
            with_muscles_primary = result.single()['count']
            
            status = {
                'total_count': count,
                'min_id': record['min_id'],
                'max_id': record['max_id'],
                'with_all_muscles_en': with_muscles_en,
                'with_muscles_tree': with_muscles_tree,
                'with_muscles_primary_tree': with_muscles_primary
            }
            
            print(f"  Exercise节点数量: {count}")
            print(f"  ID范围: {record['min_id']} - {record['max_id']}")
            print(f"  有all_muscles_en字段: {with_muscles_en}")
            print(f"  有muscles_tree字段: {with_muscles_tree}")
            print(f"  有muscles_primary_tree字段: {with_muscles_primary}")
            
            return status
    
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
        flattened['slug'] = exercise.get('slug', '')
        flattened['description_zh'] = exercise.get('description_zh_professional', '') or exercise.get('description_zh', '')
        flattened['description_en'] = exercise.get('description_en', '')
        flattened['primary_muscle_zh'] = exercise.get('primary_muscle_zh', '')
        flattened['primary_muscle_en'] = exercise.get('primary_muscle_en', '')
        
        # 肌肉群信息
        all_muscles_zh = exercise.get('all_muscles_zh', [])
        flattened['all_muscles_zh'] = all_muscles_zh if isinstance(all_muscles_zh, list) else []
        
        # 新增肌肉字段 (v2)
        all_muscles_en = exercise.get('all_muscles_en', [])
        flattened['all_muscles_en'] = all_muscles_en if isinstance(all_muscles_en, list) else []
        
        # muscles_tree - 存储为JSON字符串
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
        
        # force和mechanic可能是字典
        force = exercise.get('force', '')
        flattened['force'] = force.get('name', '') if isinstance(force, dict) else (force if force else '')
        
        mechanic = exercise.get('mechanic', '')
        flattened['mechanic'] = mechanic.get('name', '') if isinstance(mechanic, dict) else (mechanic if mechanic else '')
        
        flattened['grips'] = exercise.get('grips', []) if isinstance(exercise.get('grips'), list) else []
        
        # 动作步骤
        correct_steps_zh = exercise.get('correct_steps_zh', [])
        if isinstance(correct_steps_zh, list):
            if correct_steps_zh and isinstance(correct_steps_zh[0], dict):
                flattened['correct_steps_zh'] = [step.get('text', '') if isinstance(step, dict) else str(step) for step in correct_steps_zh]
            else:
                flattened['correct_steps_zh'] = correct_steps_zh
        else:
            flattened['correct_steps_zh'] = []
        
        correct_steps_en = exercise.get('correct_steps_en', [])
        if isinstance(correct_steps_en, list):
            if correct_steps_en and isinstance(correct_steps_en[0], dict):
                flattened['correct_steps_en'] = [step.get('text', '') if isinstance(step, dict) else str(step) for step in correct_steps_en]
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
        else:
            flattened['rep_range'] = ''
            flattened['set_range'] = ''
            flattened['rest_period'] = ''
            flattened['intensity_percentage'] = ''
            flattened['frequency'] = ''
            flattened['progression'] = ''
            flattened['technique_focus'] = []
        
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
        else:
            flattened['safety_level'] = 'MEDIUM_RISK'
            flattened['safety_pre_check'] = []
            flattened['safety_during'] = []
            flattened['safety_warning_signs'] = []
            flattened['equipment_risks'] = []
        
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
            else:
                flattened['daily_protein'] = ''
                flattened['daily_water'] = ''
                flattened['daily_rest'] = ''
        else:
            flattened['key_nutrients'] = []
            flattened['recommended_foods'] = []
            flattened['nutrition_timing'] = ''
            flattened['target_muscle_nutrition'] = ''
            flattened['daily_protein'] = ''
            flattened['daily_water'] = ''
            flattened['daily_rest'] = ''
        
        # 元数据
        enhancement_meta = exercise.get('enhancement_metadata', {})
        if isinstance(enhancement_meta, dict):
            flattened['data_source'] = enhancement_meta.get('source', 'enhanced_perfect_exercises')
            flattened['enhancement_version'] = enhancement_meta.get('version', '')
        else:
            flattened['data_source'] = 'enhanced_perfect_exercises'
            flattened['enhancement_version'] = ''
        
        return flattened

    
    def update_existing_node_ids(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        更新现有节点ID（使用临时属性避免冲突）
        
        策略：
        1. 先给所有节点添加临时属性 temp_new_id
        2. 然后批量更新 id = temp_new_id
        3. 最后删除临时属性
        
        Args:
            dry_run: 是否只模拟运行
            
        Returns:
            更新统计信息
        """
        print(f"\n🔄 更新现有节点ID...")
        
        # 构建需要更新的ID列表
        id_changes = []
        for old_id_str, new_id in self.id_mapping.items():
            old_id = int(old_id_str)
            if old_id != new_id:
                id_changes.append({'old_id': old_id, 'new_id': new_id})
        
        print(f"  需要更新 {len(id_changes)} 个节点的ID")
        
        if dry_run:
            print("  [DRY RUN] 跳过实际更新")
            return {'updated': 0, 'skipped': len(id_changes)}
        
        if not id_changes:
            print("  ✅ 没有需要更新的ID")
            return {'updated': 0, 'skipped': 0}
        
        with self.driver.session() as session:
            # 步骤1: 添加临时属性
            print("  步骤1: 添加临时属性 temp_new_id...")
            for change in id_changes:
                session.run('''
                    MATCH (e:Exercise {id: $old_id})
                    SET e.temp_new_id = $new_id
                ''', old_id=change['old_id'], new_id=change['new_id'])
            
            # 步骤2: 更新ID
            print("  步骤2: 更新ID...")
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.temp_new_id IS NOT NULL
                SET e.id = e.temp_new_id
                REMOVE e.temp_new_id
                RETURN count(e) as updated
            ''')
            updated = result.single()['updated']
            
            print(f"  ✅ 更新了 {updated} 个节点的ID")
            
        return {'updated': updated, 'skipped': 0}
    
    def add_muscle_fields(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        添加新肌肉字段到现有节点
        
        字段：all_muscles_en, muscles_tree, muscles_primary_tree
        
        Args:
            dry_run: 是否只模拟运行
            
        Returns:
            更新统计信息
        """
        print(f"\n🔄 添加新肌肉字段...")
        
        if dry_run:
            print("  [DRY RUN] 跳过实际更新")
            return {'updated': 0}
        
        updated_count = 0
        error_count = 0
        
        with self.driver.session() as session:
            for exercise_id, exercise in self.exercises.items():
                try:
                    # 准备肌肉字段数据
                    all_muscles_en = exercise.get('all_muscles_en', [])
                    if not isinstance(all_muscles_en, list):
                        all_muscles_en = []
                    
                    muscles_tree = exercise.get('muscles_tree', [])
                    muscles_tree_json = json.dumps(muscles_tree, ensure_ascii=False) if muscles_tree else '[]'
                    
                    muscles_primary_tree = exercise.get('muscles_primary_tree', [])
                    muscles_primary_tree_json = json.dumps(muscles_primary_tree, ensure_ascii=False) if muscles_primary_tree else '[]'
                    
                    # 更新节点
                    result = session.run('''
                        MATCH (e:Exercise {id: $id})
                        SET e.all_muscles_en = $all_muscles_en,
                            e.muscles_tree = $muscles_tree,
                            e.muscles_primary_tree = $muscles_primary_tree,
                            e.updated_at = datetime()
                        RETURN e.id as id
                    ''', 
                        id=exercise_id,
                        all_muscles_en=all_muscles_en,
                        muscles_tree=muscles_tree_json,
                        muscles_primary_tree=muscles_primary_tree_json
                    )
                    
                    if result.single():
                        updated_count += 1
                    
                    if updated_count % 200 == 0:
                        print(f"  进度: {updated_count}/{len(self.exercises)}")
                        
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ 更新失败 (ID: {exercise_id}): {e}")
        
        print(f"  ✅ 更新了 {updated_count} 个节点的肌肉字段")
        if error_count > 0:
            print(f"  ⚠️  失败 {error_count} 个")
        
        return {'updated': updated_count, 'errors': error_count}
    
    def create_new_nodes(self, dry_run: bool = False) -> Dict[str, Any]:
        """
        创建新Exercise节点
        
        Args:
            dry_run: 是否只模拟运行
            
        Returns:
            创建统计信息
        """
        print(f"\n🔄 创建新Exercise节点...")
        print(f"  需要创建 {len(self.new_exercise_ids)} 个新节点")
        
        if dry_run:
            print("  [DRY RUN] 跳过实际创建")
            return {'created': 0, 'skipped': len(self.new_exercise_ids)}
        
        if not self.new_exercise_ids:
            print("  ✅ 没有需要创建的新节点")
            return {'created': 0, 'skipped': 0}
        
        created_count = 0
        error_count = 0
        skipped_count = 0
        
        with self.driver.session() as session:
            for exercise_id in self.new_exercise_ids:
                try:
                    # 检查节点是否已存在
                    result = session.run('''
                        MATCH (e:Exercise {id: $id})
                        RETURN e.id as id
                    ''', id=exercise_id)
                    
                    if result.single():
                        skipped_count += 1
                        continue
                    
                    # 获取Exercise数据
                    exercise = self.exercises.get(exercise_id)
                    if not exercise:
                        print(f"  ⚠️  找不到Exercise数据 (ID: {exercise_id})")
                        error_count += 1
                        continue
                    
                    # 展开数据
                    flattened = self.flatten_exercise_data(exercise)
                    
                    # 创建节点
                    session.run('''
                        CREATE (e:Exercise {
                            id: $id,
                            name_zh: $name_zh,
                            name_en: $name_en,
                            slug: $slug,
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
                    ''', **flattened)
                    
                    created_count += 1
                    
                    if created_count % 50 == 0:
                        print(f"  进度: 创建了 {created_count} 个节点")
                        
                except Exception as e:
                    error_count += 1
                    print(f"  ❌ 创建失败 (ID: {exercise_id}): {e}")
        
        print(f"  ✅ 创建了 {created_count} 个新节点")
        if skipped_count > 0:
            print(f"  ⏭️  跳过 {skipped_count} 个已存在的节点")
        if error_count > 0:
            print(f"  ⚠️  失败 {error_count} 个")
        
        return {'created': created_count, 'skipped': skipped_count, 'errors': error_count}
    
    def verify_update(self) -> Dict[str, Any]:
        """验证更新结果"""
        print(f"\n📊 验证更新结果...")
        
        with self.driver.session() as session:
            # 统计总数
            result = session.run('MATCH (e:Exercise) RETURN count(e) as count')
            total = result.single()['count']
            
            # 检查ID范围
            result = session.run('MATCH (e:Exercise) RETURN min(e.id) as min_id, max(e.id) as max_id')
            record = result.single()
            
            # 检查新肌肉字段覆盖率
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.all_muscles_en IS NOT NULL AND size(e.all_muscles_en) > 0
                RETURN count(e) as count
            ''')
            with_muscles_en = result.single()['count']
            
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.muscles_tree IS NOT NULL AND e.muscles_tree <> '[]'
                RETURN count(e) as count
            ''')
            with_muscles_tree = result.single()['count']
            
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.muscles_primary_tree IS NOT NULL AND e.muscles_primary_tree <> '[]'
                RETURN count(e) as count
            ''')
            with_muscles_primary = result.single()['count']
            
            # 检查特定新增节点
            result = session.run('''
                MATCH (e:Exercise)
                WHERE e.id IN [96, 284, 1209]
                RETURN e.id as id, e.name_zh as name
            ''')
            new_nodes = list(result)
            
            verification = {
                'total_count': total,
                'expected_count': len(self.exercises),
                'min_id': record['min_id'],
                'max_id': record['max_id'],
                'with_all_muscles_en': with_muscles_en,
                'with_muscles_tree': with_muscles_tree,
                'with_muscles_primary_tree': with_muscles_primary,
                'new_nodes_found': len(new_nodes),
                'success': total == len(self.exercises)
            }
            
            print(f"  总节点数: {total} (期望: {len(self.exercises)})")
            print(f"  ID范围: {record['min_id']} - {record['max_id']}")
            print(f"  有all_muscles_en: {with_muscles_en} ({with_muscles_en*100//total}%)")
            print(f"  有muscles_tree: {with_muscles_tree} ({with_muscles_tree*100//total}%)")
            print(f"  有muscles_primary_tree: {with_muscles_primary} ({with_muscles_primary*100//total}%)")
            
            if new_nodes:
                print(f"\n  检查新增节点:")
                for node in new_nodes:
                    print(f"    ID {node['id']}: {node['name']}")
            
            if verification['success']:
                print(f"\n  ✅ 验证通过！")
            else:
                print(f"\n  ⚠️  节点数量不匹配")
            
            return verification
    
    def run(self, dry_run: bool = False, skip_id_update: bool = False, skip_muscle_fields: bool = False):
        """
        执行完整增量更新流程
        
        Args:
            dry_run: 是否只模拟运行
            skip_id_update: 是否跳过ID更新
            skip_muscle_fields: 是否跳过肌肉字段更新
        """
        print("=" * 60)
        print("🚀 开始增量更新Neo4j Exercise节点")
        print("=" * 60)
        
        if dry_run:
            print("⚠️  DRY RUN 模式 - 不会实际修改数据")
        
        try:
            # 1. 加载数据
            self.load_data()
            
            # 2. 检查当前状态
            status_before = self.get_current_neo4j_status()
            
            # 3. 更新现有节点ID
            if not skip_id_update:
                id_result = self.update_existing_node_ids(dry_run=dry_run)
            else:
                print("\n⏭️  跳过ID更新")
                id_result = {'skipped': True}
            
            # 4. 添加新肌肉字段
            if not skip_muscle_fields:
                muscle_result = self.add_muscle_fields(dry_run=dry_run)
            else:
                print("\n⏭️  跳过肌肉字段更新")
                muscle_result = {'skipped': True}
            
            # 5. 创建新节点
            create_result = self.create_new_nodes(dry_run=dry_run)
            
            # 6. 验证结果
            if not dry_run:
                verification = self.verify_update()
            else:
                verification = {'dry_run': True}
            
            # 7. 生成报告
            report = {
                'timestamp': datetime.now().isoformat(),
                'dry_run': dry_run,
                'status_before': status_before,
                'id_update': id_result,
                'muscle_fields': muscle_result,
                'new_nodes': create_result,
                'verification': verification
            }
            
            print("\n" + "=" * 60)
            print("✅ 增量更新完成！")
            print("=" * 60)
            
            return report
            
        except Exception as e:
            print(f"\n❌ 更新失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            self.close()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增量更新Neo4j Exercise节点')
    parser.add_argument('--dry-run', '-d', action='store_true', 
                       help='模拟运行，不实际修改数据')
    parser.add_argument('--skip-id-update', action='store_true',
                       help='跳过ID更新')
    parser.add_argument('--skip-muscle-fields', action='store_true',
                       help='跳过肌肉字段更新')
    args = parser.parse_args()
    
    # 配置路径
    project_root = Path(__file__).parent.parent.parent
    
    # 数据文件路径
    possible_data_paths = [
        project_root / "data" / "enhanced_perfect_exercises_dataset.json",
        Path("/app/data/enhanced_perfect_exercises_dataset.json"),
    ]
    
    data_file = None
    for path in possible_data_paths:
        if path.exists():
            data_file = path
            break
    
    if data_file is None:
        print("❌ 找不到增强数据集文件")
        return
    
    # 映射文件路径
    possible_mapping_paths = [
        project_root / "scripts" / "log" / "id_mapping_result.json",  # Docker容器内路径
        Path("/app/scripts/log/id_mapping_result.json"),  # Docker绝对路径
        project_root.parent / "scripts" / "log" / "id_mapping_result.json",  # 本地路径
    ]
    
    mapping_file = None
    for path in possible_mapping_paths:
        if path.exists():
            mapping_file = path
            break
    
    if mapping_file is None:
        print("❌ 找不到ID映射文件")
        print("  尝试过的路径:")
        for path in possible_mapping_paths:
            print(f"    - {path}")
        return
    
    # 从环境变量读取Neo4j配置
    neo4j_uri = os.getenv('NEO4J_URI', 'bolt://fitness_neo4j:7687')
    neo4j_user = os.getenv('NEO4J_USER', 'neo4j')
    neo4j_password = os.getenv('NEO4J_PASSWORD', 'build_body_2024')
    
    # 执行更新
    updater = ExerciseIncrementalUpdater(
        data_file=str(data_file),
        mapping_file=str(mapping_file),
        neo4j_uri=neo4j_uri,
        neo4j_user=neo4j_user,
        neo4j_password=neo4j_password
    )
    
    updater.run(
        dry_run=args.dry_run,
        skip_id_update=args.skip_id_update,
        skip_muscle_fields=args.skip_muscle_fields
    )


if __name__ == "__main__":
    main()
