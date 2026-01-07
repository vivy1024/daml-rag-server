"""
训练知识导入器测试

测试所有训练知识补充器的基本功能
"""

import pytest
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 直接导入补充器
from src.applications.fitness.data_supplement.training_volume_supplementer import TrainingVolumeSupplementer
from src.applications.fitness.data_supplement.strength_standard_supplementer import StrengthStandardSupplementer
from src.applications.fitness.data_supplement.workout_program_supplementer import WorkoutProgramSupplementer
from src.applications.fitness.data_supplement.acsm_standard_supplementer import ACSMStandardSupplementer
from src.applications.fitness.data_supplement.nsca_standard_supplementer import NSCAStandardSupplementer


class TestTrainingVolumeSupplementer:
    """测试训练量标准补充器"""
    
    def test_load_volume_data(self):
        """测试加载训练量数据"""
        # 创建补充器（不需要Neo4j驱动）
        supplementer = TrainingVolumeSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 加载数据
        volume_data = supplementer._load_volume_data()
        
        # 验证数据不为空
        assert volume_data is not None
        assert len(volume_data) > 0
        
        # 验证包含预期的肌群
        assert 'chest' in volume_data or 'front_delts' in volume_data
    
    def test_extract_volume_value(self):
        """测试提取训练量数值"""
        supplementer = TrainingVolumeSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 测试范围值
        result = supplementer._extract_volume_value({"sets_per_week": "8-10"})
        assert result == 9  # (8+10)//2
        
        # 测试单一数值
        result = supplementer._extract_volume_value({"sets_per_week": "12"})
        assert result == 12
        
        # 测试带+号的值
        result = supplementer._extract_volume_value({"sets_per_week": "22+"})
        assert result == 22
        
        # 测试0值
        result = supplementer._extract_volume_value({"sets_per_week": "0"})
        assert result == 0


class TestStrengthStandardSupplementer:
    """测试力量标准补充器"""
    
    def test_load_standards_data(self):
        """测试加载力量标准数据"""
        supplementer = StrengthStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 加载数据
        standards_data = supplementer._load_standards_data()
        
        # 验证数据不为空
        assert standards_data is not None
        assert 'male_standards_kg' in standards_data
        assert 'female_standards_kg' in standards_data
    
    def test_generate_standard_id(self):
        """测试生成力量标准ID"""
        supplementer = StrengthStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 生成ID
        standard_id = supplementer._generate_standard_id(
            exercise_key="squat",
            gender="male",
            bodyweight_kg=75.0,
            level_key="intermediate"
        )
        
        # 验证ID格式
        assert standard_id == "strength_std_squat_male_75.0_intermediate"


class TestWorkoutProgramSupplementer:
    """测试训练计划模板补充器"""
    
    def test_load_programs_data(self):
        """测试加载训练计划模板数据"""
        supplementer = WorkoutProgramSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 加载数据
        programs_data = supplementer._load_programs_data()
        
        # 验证数据不为空
        assert programs_data is not None
        assert 'programs' in programs_data
        assert len(programs_data['programs']) > 0
    
    def test_infer_training_split(self):
        """测试推断训练分化类型"""
        supplementer = WorkoutProgramSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 测试2个训练日
        result = supplementer._infer_training_split({
            "workouts": {"A": {}, "B": {}}
        })
        assert result == "上下肢分化"
        
        # 测试3个训练日
        result = supplementer._infer_training_split({
            "workouts": {"A": {}, "B": {}, "C": {}}
        })
        assert result == "全身训练"
    
    def test_infer_training_goal(self):
        """测试推断训练目标"""
        supplementer = WorkoutProgramSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 测试力量训练
        result = supplementer._infer_training_goal({
            "description": "A strength training program"
        })
        assert result == "力量提升"
        
        # 测试增肌训练
        result = supplementer._infer_training_goal({
            "description": "Hypertrophy focused program"
        })
        assert result == "肌肉增长"


class TestACSMStandardSupplementer:
    """测试ACSM标准补充器"""
    
    def test_standards_dir_exists(self):
        """测试ACSM标准目录是否存在"""
        supplementer = ACSMStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 验证目录存在
        assert supplementer.standards_dir.exists()
    
    def test_generate_standard_id(self):
        """测试生成ACSM标准ID"""
        supplementer = ACSMStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 生成ID
        standard_id = supplementer._generate_standard_id("fitt_principle_1_20251110_221821")
        
        # 验证ID格式
        assert standard_id == "acsm_std_fitt_principle_1_20251110_221821"
    
    def test_translate_title(self):
        """测试翻译标题"""
        supplementer = ACSMStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 测试翻译
        assert supplementer._translate_title("fitt_principle") == "FITT原则"
        assert supplementer._translate_title("heart_rate_guidelines") == "心率指南"


class TestNSCAStandardSupplementer:
    """测试NSCA标准补充器"""
    
    def test_standards_dir_exists(self):
        """测试NSCA标准目录是否存在"""
        supplementer = NSCAStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 验证目录存在
        assert supplementer.standards_dir.exists()
    
    def test_generate_standard_id(self):
        """测试生成NSCA标准ID"""
        supplementer = NSCAStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 生成ID
        standard_id = supplementer._generate_standard_id("strength_essentials_0_20251110_221821")
        
        # 验证ID格式
        assert standard_id == "nsca_std_strength_essentials_0_20251110_221821"
    
    def test_translate_title(self):
        """测试翻译标题"""
        supplementer = NSCAStandardSupplementer(
            neo4j_driver=None,
            data_dir="data/training_knowledge"
        )
        
        # 测试翻译
        assert supplementer._translate_title("strength_essentials") == "力量训练基础"
        assert supplementer._translate_title("periodization") == "周期化训练"


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])
