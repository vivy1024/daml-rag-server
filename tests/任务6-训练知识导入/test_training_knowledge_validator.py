"""
测试训练知识数据验证器

测试范围：
1. 训练量标准数据验证
2. 力量标准数据验证
3. 训练计划模板数据验证
4. ACSM标准数据验证
5. NSCA标准数据验证

作者：薛小川
日期：2025-12-19
"""

import json
import pytest
from pathlib import Path

pytest.importorskip(
    "src.applications.fitness.data_supplement",
    reason="data_supplement 模块已移除/未包含",
)

from src.applications.fitness.data_supplement.validator import DataValidator


class TestTrainingKnowledgeValidator:
    """测试训练知识数据验证器"""
    
    @pytest.fixture
    def validator(self):
        """创建验证器实例（不需要Neo4j连接）"""
        return DataValidator(neo4j_driver=None)
    
    @pytest.fixture
    def data_dir(self):
        """数据目录路径"""
        return Path(__file__).parent.parent / "data" / "training_knowledge"
    
    def test_validate_training_volume(self, validator, data_dir):
        """测试训练量标准数据验证"""
        # 加载真实数据
        file_path = data_dir / "training-volume-landmarks.json"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 执行验证
        result = validator.validate_training_volume(data)
        
        # 断言
        assert result.field_name == "training_volume"
        assert result.total_checked > 0
        print(f"\n训练量数据验证结果:")
        print(f"  总检查数: {result.total_checked}")
        print(f"  有效数: {result.valid_count}")
        print(f"  无效数: {result.invalid_count}")
        print(f"  有效率: {result.validity_rate:.1f}%")
        
        if result.errors:
            print(f"\n错误列表:")
            for error in result.errors[:5]:  # 只显示前5个错误
                print(f"  - {error}")
        
        # 验证应该全部通过
        assert result.is_valid, f"训练量数据验证失败: {result.errors}"
    
    def test_validate_strength_standards(self, validator, data_dir):
        """测试力量标准数据验证"""
        # 加载真实数据
        file_path = data_dir / "strength-standards.json"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 执行验证
        result = validator.validate_strength_standards(data)
        
        # 断言
        assert result.field_name == "strength_standards"
        assert result.total_checked > 0
        print(f"\n力量标准数据验证结果:")
        print(f"  总检查数: {result.total_checked}")
        print(f"  有效数: {result.valid_count}")
        print(f"  无效数: {result.invalid_count}")
        print(f"  有效率: {result.validity_rate:.1f}%")
        
        if result.errors:
            print(f"\n错误列表:")
            for error in result.errors[:5]:
                print(f"  - {error}")
        
        # 验证应该全部通过
        assert result.is_valid, f"力量标准数据验证失败: {result.errors}"
    
    def test_validate_workout_programs(self, validator, data_dir):
        """测试训练计划模板数据验证"""
        # 加载真实数据
        file_path = data_dir / "workout-programs.json"
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 执行验证
        result = validator.validate_workout_programs(data)
        
        # 断言
        assert result.field_name == "workout_programs"
        assert result.total_checked > 0
        print(f"\n训练计划模板数据验证结果:")
        print(f"  总检查数: {result.total_checked}")
        print(f"  有效数: {result.valid_count}")
        print(f"  无效数: {result.invalid_count}")
        print(f"  有效率: {result.validity_rate:.1f}%")
        
        if result.errors:
            print(f"\n错误列表:")
            for error in result.errors[:5]:
                print(f"  - {error}")
        
        # 验证应该全部通过
        assert result.is_valid, f"训练计划模板数据验证失败: {result.errors}"
    
    def test_validate_acsm_standards(self, validator, data_dir):
        """测试ACSM标准数据验证"""
        # 加载真实数据
        acsm_dir = data_dir / "acsm_standards"
        json_files = list(acsm_dir.glob("*.json"))
        
        assert len(json_files) > 0, "未找到ACSM标准数据文件"
        
        # 测试第一个文件
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 执行验证
        result = validator.validate_acsm_standards(data)
        
        # 断言
        assert result.field_name == "acsm_standards"
        print(f"\nACSM标准数据验证结果:")
        print(f"  文件: {json_files[0].name}")
        print(f"  有效: {result.is_valid}")
        
        if result.errors:
            print(f"\n错误列表:")
            for error in result.errors:
                print(f"  - {error}")
        
        # 验证应该通过
        assert result.is_valid, f"ACSM标准数据验证失败: {result.errors}"
    
    def test_validate_nsca_standards(self, validator, data_dir):
        """测试NSCA标准数据验证"""
        # 加载真实数据
        nsca_dir = data_dir / "nsca_standards"
        json_files = list(nsca_dir.glob("*.json"))
        
        assert len(json_files) > 0, "未找到NSCA标准数据文件"
        
        # 测试第一个文件
        with open(json_files[0], "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 执行验证
        result = validator.validate_nsca_standards(data)
        
        # 断言
        assert result.field_name == "nsca_standards"
        print(f"\nNSCA标准数据验证结果:")
        print(f"  文件: {json_files[0].name}")
        print(f"  有效: {result.is_valid}")
        
        if result.errors:
            print(f"\n错误列表:")
            for error in result.errors:
                print(f"  - {error}")
        
        # 验证应该通过
        assert result.is_valid, f"NSCA标准数据验证失败: {result.errors}"
    
    def test_validate_training_volume_invalid_data(self, validator):
        """测试训练量数据验证 - 无效数据"""
        # 构造无效数据：MEV > MAV
        invalid_data = {
            "volume_landmarks": {
                "chest": {
                    "MV": {"sets_per_week": "8-10"},
                    "MEV": {"sets_per_week": "20"},  # 错误：MEV > MAV
                    "MAV": {"sets_per_week": "12-20"},
                    "MRV": {"sets_per_week": "22+"}
                }
            }
        }
        
        result = validator.validate_training_volume(invalid_data)
        
        # 应该检测到错误
        assert not result.is_valid
        assert result.invalid_count > 0
        print(f"\n无效训练量数据测试:")
        print(f"  检测到错误: {len(result.errors)}")
        print(f"  错误详情: {result.errors[0]}")
    
    def test_validate_strength_standards_invalid_data(self, validator):
        """测试力量标准数据验证 - 无效数据"""
        # 构造无效数据：负数体重
        invalid_data = {
            "male_standards_kg": {
                "squat": {
                    "-60": {  # 错误：负数体重
                        "beginner": 47,
                        "novice": 70
                    }
                }
            }
        }
        
        result = validator.validate_strength_standards(invalid_data)
        
        # 应该检测到错误
        assert not result.is_valid
        assert result.invalid_count > 0
        print(f"\n无效力量标准数据测试:")
        print(f"  检测到错误: {len(result.errors)}")
        print(f"  错误详情: {result.errors[0]}")
    
    def test_validate_workout_programs_invalid_data(self, validator):
        """测试训练计划模板数据验证 - 无效数据"""
        # 构造无效数据：训练频率超出范围
        invalid_data = {
            "programs": {
                "test_program": {
                    "name": "测试计划",
                    "experience_level": "beginner",
                    "frequency_per_week": 10  # 错误：超出1-7范围
                }
            }
        }
        
        result = validator.validate_workout_programs(invalid_data)
        
        # 应该检测到错误
        assert not result.is_valid
        assert result.invalid_count > 0
        print(f"\n无效训练计划数据测试:")
        print(f"  检测到错误: {len(result.errors)}")
        print(f"  错误详情: {result.errors[0]}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
