#!/usr/bin/env python3
"""
重建muscle节点脚本
从enhanced_perfect_exercises_dataset.json提取所有肌肉数据并重建到Neo4j
"""

import json
import sys
from neo4j import GraphDatabase
from collections import defaultdict, Counter
import re

class MuscleRestorer:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def clear_muscle_nodes(self, tx):
        """清空现有muscle节点和TARGETS关系"""
        print("🗑️ 清空现有muscle节点...")
        tx.run("MATCH (m:Muscle) DETACH DELETE m")
        print("✅ 已清空所有muscle节点")

    def extract_muscle_data(self, file_path):
        """从数据文件提取肌肉信息"""
        print(f"📖 读取数据文件: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        exercises = data.get('exercises', [])
        muscle_counter = Counter()
        muscle_to_exercises = defaultdict(list)

        for ex in exercises:
            # 提取all_muscles字段
            muscles = ex.get('all_muscles', [])
            enhanced_muscles = ex.get('all_muscles_zh_enhanced', [])

            all_muscles = list(set(muscles + enhanced_muscles))

            for muscle in all_muscles:
                muscle_counter[muscle] += 1
                muscle_to_exercises[muscle].append(ex)

        print(f"✅ 从{len(exercises)}个动作中提取到{len(muscle_counter)}个唯一肌肉")

        return dict(muscle_counter), dict(muscle_to_exercises)

    def standardize_muscle_name(self, name_zh):
        """标准化肌肉名称"""
        # 中英文映射
        name_mapping = {
            '二头肌': '肱二头肌',
            '二头肌长头': '肱二头肌长头',
            '肱二头肌短头': '肱二头肌短头',
            '三头肌': '肱三头肌',
            '三头肌长头': '肱三头肌长头',
            '胸大肌': '胸部',
            '中胸与下胸': '中胸与下胸',
            '上胸': '上胸',
            '三角肌前束': '三角肌前束',
            '后束三角肌': '三角肌后束',
            '侧三角肌': '三角肌中束',
            '前肩': '三角肌前束',
            '后肩': '三角肌后束',
            '中背': '中背部',
            '上背部': '上背部',
            '下背部': '下背部',
            '斜方肌（中背）': '斜方肌中束',
            '上斜方肌': '斜方肌上束',
            '斜方肌下部': '斜方肌下束',
            '背阔肌': '背阔肌',
            '臀大肌': '臀大肌',
            '股四头肌': '股四头肌',
            '股四头肌内侧': '股四头肌内侧',
            '股四头肌外侧': '股四头肌外侧',
            '腿后肌群': '腘绳肌群',
            '腘绳肌内侧': '半膜肌',
            '前臂': '前臂肌群',
            '腕屈肌群': '腕屈肌',
            '腕伸肌群': '腕伸肌',
            '小腿': '小腿肌群',
            '腓肠肌': '腓肠肌',
            '比目鱼肌': '比目鱼肌',
            '腹肌': '腹部肌群',
            '上腹肌': '腹直肌上束',
            '下腹部': '腹直肌下束',
            '腹直肌': '腹直肌',
            '腹斜肌': '腹外斜肌',
        }

        return name_mapping.get(name_zh, name_zh)

    def get_muscle_en_name(self, name_zh):
        """获取英文名称"""
        en_mapping = {
            '肱二头肌': 'Biceps Brachii',
            '肱二头肌长头': 'Biceps Brachii Long Head',
            '肱二头肌短头': 'Biceps Brachii Short Head',
            '肱三头肌': 'Triceps Brachii',
            '肱三头肌长头': 'Triceps Brachii Long Head',
            '肱三头肌外侧头': 'Triceps Brachii Lateral Head',
            '肱三头肌内侧头': 'Triceps Brachii Medial Head',
            '胸部': 'Chest',
            '中胸与下胸': 'Mid and Lower Chest',
            '上胸': 'Upper Chest',
            '三角肌前束': 'Anterior Deltoid',
            '三角肌后束': 'Rear Deltoid',
            '三角肌中束': 'Lateral Deltoid',
            '斜方肌上束': 'Upper Trapezius',
            '斜方肌中束': 'Middle Trapezius',
            '斜方肌下束': 'Lower Trapezius',
            '背阔肌': 'Latissimus Dorsi',
            '中背部': 'Mid Back',
            '上背部': 'Upper Back',
            '下背部': 'Lower Back',
            '臀大肌': 'Gluteus Maximus',
            '臀部': 'Glutes',
            '股四头肌': 'Quadriceps Femoris',
            '股四头肌内侧': 'Vastus Medialis',
            '股四头肌外侧': 'Vastus Lateralis',
            '腘绳肌群': 'Hamstrings',
            '半膜肌': 'Semimembranosus',
            '前臂肌群': 'Forearm',
            '腕屈肌': 'Wrist Flexors',
            '腕伸肌': 'Wrist Extensors',
            '小腿肌群': 'Calves',
            '腓肠肌': 'Gastrocnemius',
            '比目鱼肌': 'Soleus',
            '腹直肌': 'Rectus Abdominis',
            '腹直肌上束': 'Upper Rectus Abdominis',
            '腹直肌下束': 'Lower Rectus Abdominis',
            '腹外斜肌': 'External Oblique',
            '腹部肌群': 'Abdominals',
            '腹股沟': 'Hip Adductors',
            '肩部': 'Shoulders',
            '手': 'Hands',
        }

        return en_mapping.get(name_zh, name_zh)

    def get_muscle_category(self, name_zh):
        """确定肌肉分类"""
        primary_muscles = {
            '胸部', '背阔肌', '股四头肌', '腘绳肌群', '臀大肌',
            '肱二头肌', '肱三头肌', '三角肌前束', '三角肌后束', '三角肌中束',
            '腹部肌群', '小腿肌群', '前臂肌群', '斜方肌上束', '斜方肌中束', '斜方肌下束',
            '下背部'
        }

        return 'primary' if name_zh in primary_muscles else 'secondary'

    def get_training_volume(self, name_zh):
        """获取训练容量数据 (MEV/MAV/MRV)"""
        # 标准训练容量数据
        volume_data = {
            '胸部': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '中胸与下胸': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '上胸': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '背阔肌': {'MEV': 12, 'MAV': 24, 'MRV': 30},
            '中背部': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '上背部': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '下背部': {'MEV': 12, 'MAV': 24, 'MRV': 30},
            '肱二头肌': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '肱二头肌长头': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '肱二头肌短头': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '肱三头肌': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '肱三头肌长头': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '肱三头肌外侧头': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '肱三头肌内侧头': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '三角肌前束': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '三角肌后束': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '三角肌中束': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '斜方肌上束': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '斜方肌中束': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '斜方肌下束': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '臀大肌': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '臀部': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '股四头肌': {'MEV': 12, 'MAV': 24, 'MRV': 30},
            '股四头肌内侧': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '股四头肌外侧': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '腘绳肌群': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '半膜肌': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '小腿肌群': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '腓肠肌': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '比目鱼肌': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '腹直肌': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '腹直肌上束': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '腹直肌下束': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '腹外斜肌': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '腹部肌群': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '前臂肌群': {'MEV': 8, 'MAV': 16, 'MRV': 22},
            '腕屈肌': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '腕伸肌': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '腹股沟': {'MEV': 6, 'MAV': 12, 'MRV': 18},
            '肩部': {'MEV': 10, 'MAV': 20, 'MRV': 26},
            '手': {'MEV': 4, 'MAV': 8, 'MRV': 12},
        }

        return volume_data.get(name_zh, {'MEV': 8, 'MAV': 16, 'MRV': 22})

    def create_muscle_nodes(self, tx, muscle_counter):
        """创建muscle节点"""
        print("\n🏗️ 创建muscle节点...")

        muscles = sorted(muscle_counter.keys(), key=lambda x: x)
        created_count = 0

        for i, muscle_zh in enumerate(muscles, 1):
            # 标准化名称
            standard_name = self.standardize_muscle_name(muscle_zh)
            name_en = self.get_muscle_en_name(standard_name)
            category = self.get_muscle_category(standard_name)
            volume = self.get_training_volume(standard_name)
            frequency = muscle_counter[muscle_zh]

            # 创建节点
            tx.run("""
                CREATE (m:Muscle {
                    id: $id,
                    name_zh: $name_zh,
                    name_en: $name_en,
                    category: $category,
                    training_frequency: $frequency,
                    MEV: $mev,
                    MAV: $mav,
                    MRV: $mrv,
                    evidence_level: 'Professional Standard',
                    reliability_score: 95,
                    function: $function,
                    movement_patterns: $patterns,
                    recovery_time: $recovery,
                    synergy_partners: $synergy,
                    antagonist_partners: $antagonist,
                    group: $group,
                    created_at: datetime()
                })
            """, id=f"muscle_{i:03d}",
                   name_zh=standard_name,
                   name_en=name_en,
                   category=category,
                   frequency=frequency,
                   mev=volume['MEV'],
                   mav=volume['MAV'],
                   mrv=volume['MRV'],
                   function=self.get_muscle_function(standard_name),
                   patterns=self.get_movement_patterns(standard_name),
                   recovery=self.get_recovery_time(standard_name),
                   synergy=self.get_synergy_partners(standard_name),
                   antagonist=self.get_antagonist_partners(standard_name),
                   group=self.get_muscle_group(standard_name))

            created_count += 1
            print(f"  {created_count:3d}. {standard_name} ({name_en}) - {category}, 频次:{frequency}")

        print(f"\n✅ 成功创建{created_count}个muscle节点")

    def get_muscle_function(self, name_zh):
        """获取肌肉功能"""
        functions = {
            '胸部': '胸廓屈曲、肩关节屈曲',
            '背阔肌': '肩关节伸展、内收、内旋',
            '股四头肌': '膝关节伸展、髋关节屈曲',
            '腘绳肌群': '膝关节屈曲、髋关节伸展',
            '臀大肌': '髋关节伸展、外展、外旋',
            '肱二头肌': '肘关节屈曲、前臂旋后',
            '肱三头肌': '肘关节伸展、肩关节伸展',
            '三角肌前束': '肩关节屈曲、内旋',
            '三角肌后束': '肩关节伸展、外旋',
            '三角肌中束': '肩关节外展',
            '腹直肌': '脊柱屈曲、骨盆后倾',
            '下背部': '脊柱伸展、维持姿势',
        }
        return functions.get(name_zh, '运动功能')

    def get_movement_patterns(self, name_zh):
        """获取运动模式"""
        patterns = ['推', '拉', '蹲', '硬拉', '旋转']
        return patterns

    def get_recovery_time(self, name_zh):
        """获取恢复时间"""
        return '48-72小时'

    def get_synergy_partners(self, name_zh):
        """获取协同肌"""
        partners = {
            '胸部': ['三角肌前束', '肱三头肌'],
            '背阔肌': ['肱二头肌', '三角肌后束'],
            '股四头肌': ['臀大肌', '小腿肌群'],
        }
        return partners.get(name_zh, [])

    def get_antagonist_partners(self, name_zh):
        """获取对抗肌"""
        pairs = {
            '肱二头肌': '肱三头肌',
            '肱三头肌': '肱二头肌',
            '三角肌前束': '三角肌后束',
            '三角肌后束': '三角肌前束',
            '股四头肌': '腘绳肌群',
            '腘绳肌群': '股四头肌',
            '腹直肌': '下背部',
            '胸部': '中背部',
        }
        return [pairs.get(name_zh, '')]

    def get_muscle_group(self, name_zh):
        """获取肌群"""
        groups = {
            '胸部': '上肢推',
            '背阔肌': '上肢拉',
            '肱二头肌': '上肢屈肌',
            '肱三头肌': '上肢伸肌',
            '三角肌': '肩部',
            '股四头肌': '下肢伸肌',
            '腘绳肌群': '下肢屈肌',
            '臀大肌': '臀部',
            '腹直肌': '核心',
        }
        return groups.get(name_zh, '其他')

    def create_targets_relationships(self, tx, muscle_to_exercises):
        """创建TARGETS关系"""
        print("\n🔗 重建TARGETS关系...")

        total_relationships = 0
        primary_count = 0
        secondary_count = 0

        for muscle_name, exercises in muscle_to_exercises.items():
            # 标准化名称
            standard_name = self.standardize_muscle_name(muscle_name)

            # 获取Exercise ID列表（使用name_zh作为ID）
            exercise_ids = []
            for ex in exercises:
                if 'name_zh' in ex:
                    exercise_ids.append(ex['name_zh'])

            if not exercise_ids:
                continue

            # 标记主要目标（基于primary_muscle字段）
            for ex in exercises:
                primary_muscle = ex.get('primary_muscle_zh', '')
                is_primary = False

                # 检查是否匹配主要肌肉
                if primary_muscle:
                    # 直接匹配
                    if primary_muscle == muscle_name or primary_muscle == standard_name:
                        is_primary = True
                    # 模糊匹配
                    elif muscle_name in primary_muscle or primary_muscle in muscle_name:
                        is_primary = True
                    elif standard_name in primary_muscle or primary_muscle in standard_name:
                        is_primary = True

                relationship_type = "TARGETS_PRIMARY" if is_primary else "TARGETS_SECONDARY"

                # 创建关系
                tx.run(f"""
                    MATCH (e:Exercise {{name_zh: $exercise_name}})
                    MATCH (m:Muscle {{name_zh: $muscle_name}})
                    MERGE (e)-[:{relationship_type}]->(m)
                """, exercise_name=ex.get('name_zh'), muscle_name=standard_name)

                total_relationships += 1
                if is_primary:
                    primary_count += 1
                else:
                    secondary_count += 1

        print(f"✅ 成功创建{total_relationships}个TARGETS关系")
        print(f"   - TARGETS_PRIMARY: {primary_count}")
        print(f"   - TARGETS_SECONDARY: {secondary_count}")

    def verify_restoration(self, tx):
        """验证恢复结果"""
        print("\n📊 验证恢复结果...")

        # 统计muscle节点
        result = tx.run("MATCH (m:Muscle) RETURN count(m) as muscle_count")
        muscle_count = result.single()['muscle_count']

        # 统计关系
        rel_result = tx.run("""
            MATCH ()-[r:TARGETS_PRIMARY|TARGETS_SECONDARY]->()
            RETURN
                count(r) as total_relationships,
                count(CASE WHEN type(r) = 'TARGETS_PRIMARY' THEN 1 END) as primary_count,
                count(CASE WHEN type(r) = 'TARGETS_SECONDARY' THEN 1 END) as secondary_count
        """)
        rel_data = rel_result.single()

        # 检查字段完整性
        field_result = tx.run("""
            MATCH (m:Muscle)
            WHERE m.name_zh IS NOT NULL
              AND m.name_en IS NOT NULL
              AND m.MEV IS NOT NULL
              AND m.MAV IS NOT NULL
              AND m.MRV IS NOT NULL
              AND m.training_frequency IS NOT NULL
            RETURN count(m) as complete_nodes
        """)
        complete_count = field_result.single()['complete_nodes']

        print(f"✅ Muscle节点总数: {muscle_count}")
        print(f"✅ TARGETS关系总数: {rel_data['total_relationships']}")
        print(f"   - TARGETS_PRIMARY: {rel_data['primary_count']}")
        print(f"   - TARGETS_SECONDARY: {rel_data['secondary_count']}")
        print(f"✅ 完整字段节点: {complete_count}/{muscle_count}")

        if muscle_count >= 50 and rel_data['total_relationships'] >= 2000:
            print("\n🎉 恢复成功！数据质量达标")
            return True
        else:
            print("\n⚠️ 恢复不完整，需要进一步处理")
            return False

    def run(self, data_file):
        """执行完整恢复流程"""
        print("=" * 60)
        print("🚀 Neo4j Muscle节点恢复工具")
        print("=" * 60)

        with self.driver.session() as session:
            # 1. 清空现有数据
            session.execute_write(self.clear_muscle_nodes)

            # 2. 提取肌肉数据
            muscle_counter, muscle_to_exercises = self.extract_muscle_data(data_file)

            # 3. 创建muscle节点
            session.execute_write(self.create_muscle_nodes, muscle_counter)

            # 4. 重建关系
            session.execute_write(self.create_targets_relationships, muscle_to_exercises)

            # 5. 验证结果
            success = session.execute_write(self.verify_restoration)

            if success:
                print("\n✨ 恢复完成！所有数据已成功重建")
            else:
                print("\n⚠️ 恢复过程中出现问题，请检查日志")

        self.close()


if __name__ == "__main__":
    # Neo4j连接配置
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = "neo4j"
    NEO4J_PASSWORD = "fitness_neo4j_2024"

    # 数据文件路径
    DATA_FILE = "F:/build_body/mcp-servers/daml-rag-server/data/enhanced_perfect_exercises_dataset.json"

    # 执行恢复
    restorer = MuscleRestorer(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)
    try:
        restorer.run(DATA_FILE)
    except Exception as e:
        print(f"\n❌ 恢复失败: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
