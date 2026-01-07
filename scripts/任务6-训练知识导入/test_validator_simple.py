"""
简化版训练知识数据验证器测试

直接包含必要的类定义，避免复杂的导入问题

作者：薛小川
日期：2025-12-19
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


# ============================================================================
# 数据模型定义
# ============================================================================

@dataclass
class ValidationResult:
    """数据验证结果"""
    field_name: str
    total_checked: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """是否全部有效"""
        return self.invalid_count == 0
    
    @property
    def validity_rate(self) -> float:
        """有效率"""
        if self.total_checked == 0:
            return 0.0
        return self.valid_count / self.total_checked * 100


# ============================================================================
# 验证器类定义
# ============================================================================

class DataValidator:
    """数据验证器"""
    
    def __init__(self, neo4j_driver=None):
        """初始化验证器"""
        self.driver = neo4j_driver
    
    def validate_training_volume(self, data: Dict[str, Any]) -> ValidationResult:
        """验证训练量标准数据格式"""
        result = ValidationResult(field_name="training_volume")
        errors = []
        
        try:
            if "volume_landmarks" not in data:
                errors.append({
                    "error": "missing_field",
                    "field": "volume_landmarks",
                    "message": "缺少volume_landmarks字段"
                })
                result.errors = errors
                result.invalid_count = 1
                return result
            
            volume_landmarks = data["volume_landmarks"]
            
            for muscle_name, muscle_data in volume_landmarks.items():
                result.total_checked += 1
                
                # 处理嵌套结构（如shoulders）
                if isinstance(muscle_data, dict) and any(
                    key in muscle_data for key in ["front_delts", "side_delts", "rear_delts"]
                ):
                    for sub_muscle, sub_data in muscle_data.items():
                        if sub_muscle == "optimal_frequency":
                            continue
                        
                        result.total_checked += 1
                        is_valid, error = self._validate_volume_entry(
                            f"{muscle_name}.{sub_muscle}", sub_data
                        )
                        
                        if is_valid:
                            result.valid_count += 1
                        else:
                            result.invalid_count += 1
                            errors.append(error)
                else:
                    is_valid, error = self._validate_volume_entry(muscle_name, muscle_data)
                    
                    if is_valid:
                        result.valid_count += 1
                    else:
                        result.invalid_count += 1
                        errors.append(error)
            
            result.errors = errors
            
        except Exception as e:
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = result.total_checked
        
        return result
    
    def _validate_volume_entry(
        self, muscle_name: str, muscle_data: Dict[str, Any]
    ) -> tuple:
        """验证单个肌群的训练量数据"""
        required_fields = ["MV", "MEV", "MAV", "MRV"]
        missing_fields = [f for f in required_fields if f not in muscle_data]
        
        if missing_fields:
            return False, {
                "error": "missing_fields",
                "muscle": muscle_name,
                "missing": missing_fields,
                "message": f"{muscle_name} 缺少必需字段: {', '.join(missing_fields)}"
            }
        
        try:
            mv = self._extract_volume_number(muscle_data["MV"]["sets_per_week"])
            mev = self._extract_volume_number(muscle_data["MEV"]["sets_per_week"])
            mav = self._extract_volume_number(muscle_data["MAV"]["sets_per_week"])
            mrv = self._extract_volume_number(muscle_data["MRV"]["sets_per_week"])
        except (ValueError, KeyError) as e:
            return False, {
                "error": "invalid_format",
                "muscle": muscle_name,
                "message": f"{muscle_name} 数值格式错误: {str(e)}"
            }
        
        if not (mv <= mev < mav < mrv):
            return False, {
                "error": "invalid_relationship",
                "muscle": muscle_name,
                "values": {"MV": mv, "MEV": mev, "MAV": mav, "MRV": mrv},
                "message": f"{muscle_name} 数值关系错误: MV({mv}) <= MEV({mev}) < MAV({mav}) < MRV({mrv})"
            }
        
        if any(v < 0 for v in [mv, mev, mav, mrv]):
            return False, {
                "error": "negative_value",
                "muscle": muscle_name,
                "values": {"MV": mv, "MEV": mev, "MAV": mav, "MRV": mrv},
                "message": f"{muscle_name} 包含负数值"
            }
        
        return True, None
    
    def _extract_volume_number(self, volume_str: str) -> int:
        """从训练量字符串中提取数值"""
        volume_str = str(volume_str).strip()
        
        if "+" in volume_str:
            return int(volume_str.replace("+", ""))
        
        if "-" in volume_str:
            return int(volume_str.split("-")[0])
        
        return int(volume_str)
    
    def validate_strength_standards(self, data: Dict[str, Any]) -> ValidationResult:
        """验证力量标准数据格式"""
        result = ValidationResult(field_name="strength_standards")
        errors = []
        
        try:
            valid_levels = ["beginner", "novice", "intermediate", "advanced", "elite"]
            
            for gender_key in ["male_standards_kg", "female_standards_kg"]:
                if gender_key not in data:
                    errors.append({
                        "error": "missing_field",
                        "field": gender_key,
                        "message": f"缺少{gender_key}字段"
                    })
                    continue
                
                gender = "male" if "male" in gender_key else "female"
                standards = data[gender_key]
                
                for exercise_name, bodyweight_data in standards.items():
                    for bodyweight_str, level_data in bodyweight_data.items():
                        result.total_checked += 1
                        
                        try:
                            bodyweight_kg = float(bodyweight_str)
                            
                            if bodyweight_kg <= 0:
                                result.invalid_count += 1
                                errors.append({
                                    "error": "invalid_bodyweight",
                                    "exercise": exercise_name,
                                    "gender": gender,
                                    "bodyweight": bodyweight_kg,
                                    "message": f"{exercise_name} 体重值必须为正数: {bodyweight_kg}"
                                })
                                continue
                            
                            all_levels_valid = True
                            for level, weight_kg in level_data.items():
                                if level not in valid_levels:
                                    result.invalid_count += 1
                                    errors.append({
                                        "error": "invalid_level",
                                        "exercise": exercise_name,
                                        "gender": gender,
                                        "bodyweight": bodyweight_kg,
                                        "level": level,
                                        "message": f"无效的训练水平: {level}"
                                    })
                                    all_levels_valid = False
                                    break
                                
                                if weight_kg <= 0:
                                    result.invalid_count += 1
                                    errors.append({
                                        "error": "invalid_weight",
                                        "exercise": exercise_name,
                                        "gender": gender,
                                        "bodyweight": bodyweight_kg,
                                        "level": level,
                                        "weight": weight_kg,
                                        "message": f"力量值必须为正数: {weight_kg}"
                                    })
                                    all_levels_valid = False
                                    break
                            
                            if all_levels_valid:
                                result.valid_count += 1
                        
                        except ValueError as e:
                            result.invalid_count += 1
                            errors.append({
                                "error": "invalid_format",
                                "exercise": exercise_name,
                                "gender": gender,
                                "bodyweight": bodyweight_str,
                                "message": f"体重格式错误: {str(e)}"
                            })
            
            result.errors = errors
            
        except Exception as e:
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = result.total_checked
        
        return result
    
    def validate_workout_programs(self, data: Dict[str, Any]) -> ValidationResult:
        """验证训练计划模板数据格式"""
        result = ValidationResult(field_name="workout_programs")
        errors = []
        
        try:
            valid_levels = ["beginner", "intermediate", "advanced"]
            
            if "programs" not in data:
                errors.append({
                    "error": "missing_field",
                    "field": "programs",
                    "message": "缺少programs字段"
                })
                result.errors = errors
                result.invalid_count = 1
                return result
            
            programs = data["programs"]
            
            for program_id, program_data in programs.items():
                result.total_checked += 1
                
                required_fields = ["name", "experience_level"]
                missing_fields = [f for f in required_fields if f not in program_data]
                
                if missing_fields:
                    result.invalid_count += 1
                    errors.append({
                        "error": "missing_fields",
                        "program": program_id,
                        "missing": missing_fields,
                        "message": f"{program_id} 缺少必需字段: {', '.join(missing_fields)}"
                    })
                    continue
                
                experience_level = program_data.get("experience_level")
                if experience_level not in valid_levels:
                    result.invalid_count += 1
                    errors.append({
                        "error": "invalid_experience_level",
                        "program": program_id,
                        "level": experience_level,
                        "message": f"{program_id} 无效的训练水平: {experience_level}"
                    })
                    continue
                
                frequency = program_data.get("frequency_per_week")
                if frequency is not None:
                    if isinstance(frequency, str):
                        if "-" in frequency:
                            try:
                                min_freq = int(frequency.split("-")[0])
                                max_freq = int(frequency.split("-")[1])
                                if not (1 <= min_freq <= 7 and 1 <= max_freq <= 7):
                                    result.invalid_count += 1
                                    errors.append({
                                        "error": "invalid_frequency",
                                        "program": program_id,
                                        "frequency": frequency,
                                        "message": f"{program_id} 训练频率超出范围(1-7天): {frequency}"
                                    })
                                    continue
                            except ValueError:
                                result.invalid_count += 1
                                errors.append({
                                    "error": "invalid_frequency_format",
                                    "program": program_id,
                                    "frequency": frequency,
                                    "message": f"{program_id} 训练频率格式错误: {frequency}"
                                })
                                continue
                    else:
                        try:
                            freq_num = int(frequency)
                            if not (1 <= freq_num <= 7):
                                result.invalid_count += 1
                                errors.append({
                                    "error": "invalid_frequency",
                                    "program": program_id,
                                    "frequency": freq_num,
                                    "message": f"{program_id} 训练频率超出范围(1-7天): {freq_num}"
                                })
                                continue
                        except ValueError:
                            result.invalid_count += 1
                            errors.append({
                                "error": "invalid_frequency_format",
                                "program": program_id,
                                "frequency": frequency,
                                "message": f"{program_id} 训练频率格式错误: {frequency}"
                            })
                            continue
                
                result.valid_count += 1
            
            result.errors = errors
            
        except Exception as e:
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = result.total_checked
        
        return result
    
    def validate_acsm_standards(self, data: Dict[str, Any]) -> ValidationResult:
        """验证ACSM标准数据格式"""
        result = ValidationResult(field_name="acsm_standards")
        errors = []
        
        try:
            result.total_checked = 1
            
            required_fields = ["data_type", "content"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_fields",
                    "missing": missing_fields,
                    "message": f"缺少必需字段: {', '.join(missing_fields)}"
                })
                result.errors = errors
                return result
            
            content = data.get("content")
            if not content or not isinstance(content, dict):
                result.invalid_count = 1
                errors.append({
                    "error": "invalid_content",
                    "message": "content字段为空或格式错误"
                })
                result.errors = errors
                return result
            
            if "metadata" not in data:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_metadata",
                    "message": "缺少metadata字段"
                })
                result.errors = errors
                return result
            
            result.valid_count = 1
            result.errors = errors
            
        except Exception as e:
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = 1
        
        return result
    
    def validate_nsca_standards(self, data: Dict[str, Any]) -> ValidationResult:
        """验证NSCA标准数据格式"""
        result = ValidationResult(field_name="nsca_standards")
        errors = []
        
        try:
            result.total_checked = 1
            
            required_fields = ["data_type", "content"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_fields",
                    "missing": missing_fields,
                    "message": f"缺少必需字段: {', '.join(missing_fields)}"
                })
                result.errors = errors
                return result
            
            content = data.get("content")
            if not content or not isinstance(content, dict):
                result.invalid_count = 1
                errors.append({
                    "error": "invalid_content",
                    "message": "content字段为空或格式错误"
                })
                result.errors = errors
                return result
            
            if "metadata" not in data:
                result.invalid_count = 1
                errors.append({
                    "error": "missing_metadata",
                    "message": "缺少metadata字段"
                })
                result.errors = errors
                return result
            
            result.valid_count = 1
            result.errors = errors
            
        except Exception as e:
            errors.append({
                "error": "validation_exception",
                "message": str(e)
            })
            result.errors = errors
            result.invalid_count = 1
        
        return result


# ============================================================================
# 测试函数
# ============================================================================

def test_training_volume_validation():
    """测试训练量标准数据验证"""
    print("=" * 60)
    print("测试训练量标准数据验证")
    print("=" * 60)
    
    validator = DataValidator()
    
    data_file = Path("/app/data/training_knowledge/training-volume-landmarks.json")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    result = validator.validate_training_volume(data)
    
    print(f"\n验证结果:")
    print(f"  总检查数: {result.total_checked}")
    print(f"  有效数: {result.valid_count}")
    print(f"  无效数: {result.invalid_count}")
    print(f"  有效率: {result.validity_rate:.1f}%")
    print(f"  是否全部有效: {'✅ 是' if result.is_valid else '❌ 否'}")
    
    if result.errors:
        print(f"\n错误列表 (前5个):")
        for i, error in enumerate(result.errors[:5], 1):
            print(f"  {i}. {error}")
    
    return result.is_valid


def test_strength_standards_validation():
    """测试力量标准数据验证"""
    print("\n" + "=" * 60)
    print("测试力量标准数据验证")
    print("=" * 60)
    
    validator = DataValidator()
    
    data_file = Path("/app/data/training_knowledge/strength-standards.json")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    result = validator.validate_strength_standards(data)
    
    print(f"\n验证结果:")
    print(f"  总检查数: {result.total_checked}")
    print(f"  有效数: {result.valid_count}")
    print(f"  无效数: {result.invalid_count}")
    print(f"  有效率: {result.validity_rate:.1f}%")
    print(f"  是否全部有效: {'✅ 是' if result.is_valid else '❌ 否'}")
    
    if result.errors:
        print(f"\n错误列表 (前5个):")
        for i, error in enumerate(result.errors[:5], 1):
            print(f"  {i}. {error}")
    
    return result.is_valid


def test_workout_programs_validation():
    """测试训练计划模板数据验证"""
    print("\n" + "=" * 60)
    print("测试训练计划模板数据验证")
    print("=" * 60)
    
    validator = DataValidator()
    
    data_file = Path("/app/data/training_knowledge/workout-programs.json")
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    result = validator.validate_workout_programs(data)
    
    print(f"\n验证结果:")
    print(f"  总检查数: {result.total_checked}")
    print(f"  有效数: {result.valid_count}")
    print(f"  无效数: {result.invalid_count}")
    print(f"  有效率: {result.validity_rate:.1f}%")
    print(f"  是否全部有效: {'✅ 是' if result.is_valid else '❌ 否'}")
    
    if result.errors:
        print(f"\n错误列表 (前5个):")
        for i, error in enumerate(result.errors[:5], 1):
            print(f"  {i}. {error}")
    
    return result.is_valid


def test_acsm_standards_validation():
    """测试ACSM标准数据验证"""
    print("\n" + "=" * 60)
    print("测试ACSM标准数据验证")
    print("=" * 60)
    
    validator = DataValidator()
    
    acsm_dir = Path("/app/data/training_knowledge/acsm_standards")
    json_files = list(acsm_dir.glob("*.json"))
    
    if not json_files:
        print("❌ 未找到ACSM标准数据文件")
        return False
    
    print(f"\n找到 {len(json_files)} 个ACSM标准文件")
    
    all_valid = True
    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        result = validator.validate_acsm_standards(data)
        
        status = "✅" if result.is_valid else "❌"
        print(f"  {status} {json_file.name}: {'有效' if result.is_valid else '无效'}")
        
        if not result.is_valid:
            all_valid = False
            for error in result.errors:
                print(f"      错误: {error}")
    
    return all_valid


def test_nsca_standards_validation():
    """测试NSCA标准数据验证"""
    print("\n" + "=" * 60)
    print("测试NSCA标准数据验证")
    print("=" * 60)
    
    validator = DataValidator()
    
    nsca_dir = Path("/app/data/training_knowledge/nsca_standards")
    json_files = list(nsca_dir.glob("*.json"))
    
    if not json_files:
        print("❌ 未找到NSCA标准数据文件")
        return False
    
    print(f"\n找到 {len(json_files)} 个NSCA标准文件")
    
    all_valid = True
    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        result = validator.validate_nsca_standards(data)
        
        status = "✅" if result.is_valid else "❌"
        print(f"  {status} {json_file.name}: {'有效' if result.is_valid else '无效'}")
        
        if not result.is_valid:
            all_valid = False
            for error in result.errors:
                print(f"      错误: {error}")
    
    return all_valid


def test_invalid_data():
    """测试无效数据检测"""
    print("\n" + "=" * 60)
    print("测试无效数据检测")
    print("=" * 60)
    
    validator = DataValidator()
    
    # 测试1: 训练量数据 - MEV > MAV
    print("\n1. 测试训练量数据 - MEV > MAV (应该检测到错误)")
    invalid_volume = {
        "volume_landmarks": {
            "chest": {
                "MV": {"sets_per_week": "8-10"},
                "MEV": {"sets_per_week": "20"},  # 错误：MEV > MAV
                "MAV": {"sets_per_week": "12-20"},
                "MRV": {"sets_per_week": "22+"}
            }
        }
    }
    result = validator.validate_training_volume(invalid_volume)
    print(f"   结果: {'✅ 检测到错误' if not result.is_valid else '❌ 未检测到错误'}")
    if result.errors:
        print(f"   错误: {result.errors[0]}")
    
    # 测试2: 力量标准 - 负数体重
    print("\n2. 测试力量标准 - 负数体重 (应该检测到错误)")
    invalid_strength = {
        "male_standards_kg": {
            "squat": {
                "-60": {  # 错误：负数体重
                    "beginner": 47,
                    "novice": 70
                }
            }
        }
    }
    result = validator.validate_strength_standards(invalid_strength)
    print(f"   结果: {'✅ 检测到错误' if not result.is_valid else '❌ 未检测到错误'}")
    if result.errors:
        print(f"   错误: {result.errors[0]}")
    
    # 测试3: 训练计划 - 训练频率超出范围
    print("\n3. 测试训练计划 - 训练频率超出范围 (应该检测到错误)")
    invalid_program = {
        "programs": {
            "test_program": {
                "name": "测试计划",
                "experience_level": "beginner",
                "frequency_per_week": 10  # 错误：超出1-7范围
            }
        }
    }
    result = validator.validate_workout_programs(invalid_program)
    print(f"   结果: {'✅ 检测到错误' if not result.is_valid else '❌ 未检测到错误'}")
    if result.errors:
        print(f"   错误: {result.errors[0]}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("训练知识数据验证器测试")
    print("=" * 60)
    
    results = []
    
    # 运行所有测试
    results.append(("训练量标准", test_training_volume_validation()))
    results.append(("力量标准", test_strength_standards_validation()))
    results.append(("训练计划模板", test_workout_programs_validation()))
    results.append(("ACSM标准", test_acsm_standards_validation()))
    results.append(("NSCA标准", test_nsca_standards_validation()))
    
    # 测试无效数据检测
    test_invalid_data()
    
    # 输出总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {status} {name}")
    
    all_passed = all(passed for _, passed in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有测试通过！")
    else:
        print("❌ 部分测试失败")
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
