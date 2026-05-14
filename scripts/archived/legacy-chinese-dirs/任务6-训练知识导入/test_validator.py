"""
独立测试训练知识数据验证器

不依赖完整的模块导入，直接测试验证逻辑

作者：薛小川
日期：2025-12-19
"""

import json
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入validator和models，避免通过__init__.py导入manager
import importlib.util

# 加载models模块
models_path = project_root / "src" / "applications" / "fitness" / "data_supplement" / "models.py"
spec = importlib.util.spec_from_file_location("models", models_path)
models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(models)

# 加载validator模块
validator_path = project_root / "src" / "applications" / "fitness" / "data_supplement" / "validator.py"
spec = importlib.util.spec_from_file_location("validator", validator_path)
validator_module = importlib.util.module_from_spec(spec)

# 注入models到validator的命名空间
sys.modules['src.applications.fitness.data_supplement.models'] = models
validator_module.ValidationResult = models.ValidationResult

spec.loader.exec_module(validator_module)

DataValidator = validator_module.DataValidator


def test_training_volume_validation():
    """测试训练量标准数据验证"""
    print("=" * 60)
    print("测试训练量标准数据验证")
    print("=" * 60)
    
    # 创建验证器（不需要Neo4j连接）
    validator = DataValidator(neo4j_driver=None)
    
    # 加载真实数据
    data_file = project_root / "data" / "training_knowledge" / "training-volume-landmarks.json"
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 执行验证
    result = validator.validate_training_volume(data)
    
    # 输出结果
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
    
    validator = DataValidator(neo4j_driver=None)
    
    data_file = project_root / "data" / "training_knowledge" / "strength-standards.json"
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
    
    validator = DataValidator(neo4j_driver=None)
    
    data_file = project_root / "data" / "training_knowledge" / "workout-programs.json"
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
    
    validator = DataValidator(neo4j_driver=None)
    
    acsm_dir = project_root / "data" / "training_knowledge" / "acsm_standards"
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
    
    validator = DataValidator(neo4j_driver=None)
    
    nsca_dir = project_root / "data" / "training_knowledge" / "nsca_standards"
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
    
    validator = DataValidator(neo4j_driver=None)
    
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
    sys.exit(main())
