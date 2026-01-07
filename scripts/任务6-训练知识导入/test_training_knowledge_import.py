"""
训练知识导入器简单测试脚本

直接测试各个补充器的数据加载功能
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 直接导入补充器类（避免通过__init__.py）
import importlib.util

def load_module_from_file(module_name, file_path):
    """从文件路径加载模块"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_training_volume_supplementer():
    """测试训练量标准补充器"""
    print("\n" + "="*60)
    print("测试训练量标准补充器")
    print("="*60)
    
    # 加载模块
    module_path = project_root / "src/applications/fitness/data_supplement/training_volume_supplementer.py"
    module = load_module_from_file("training_volume_supplementer", module_path)
    
    # 创建补充器
    supplementer = module.TrainingVolumeSupplementer(
        neo4j_driver=None,
        data_dir="data/training_knowledge"
    )
    
    # 测试加载数据
    volume_data = supplementer._load_volume_data()
    print(f"✅ 成功加载训练量数据: {len(volume_data)} 个肌群")
    
    # 测试提取数值
    test_cases = [
        ({"sets_per_week": "8-10"}, 9),
        ({"sets_per_week": "12"}, 12),
        ({"sets_per_week": "22+"}, 22),
        ({"sets_per_week": "0"}, 0),
    ]
    
    for test_input, expected in test_cases:
        result = supplementer._extract_volume_value(test_input)
        assert result == expected, f"期望 {expected}, 得到 {result}"
        print(f"✅ 提取数值测试通过: {test_input} -> {result}")
    
    print("✅ 训练量标准补充器测试通过")


def test_strength_standard_supplementer():
    """测试力量标准补充器"""
    print("\n" + "="*60)
    print("测试力量标准补充器")
    print("="*60)
    
    # 加载模块
    module_path = project_root / "src/applications/fitness/data_supplement/strength_standard_supplementer.py"
    module = load_module_from_file("strength_standard_supplementer", module_path)
    
    # 创建补充器
    supplementer = module.StrengthStandardSupplementer(
        neo4j_driver=None,
        data_dir="data/training_knowledge"
    )
    
    # 测试加载数据
    standards_data = supplementer._load_standards_data()
    assert 'male_standards_kg' in standards_data
    assert 'female_standards_kg' in standards_data
    print(f"✅ 成功加载力量标准数据")
    
    # 测试生成ID
    standard_id = supplementer._generate_standard_id(
        exercise_key="squat",
        gender="male",
        bodyweight_kg=75.0,
        level_key="intermediate"
    )
    assert standard_id == "strength_std_squat_male_75.0_intermediate"
    print(f"✅ 生成ID测试通过: {standard_id}")
    
    print("✅ 力量标准补充器测试通过")


def test_workout_program_supplementer():
    """测试训练计划模板补充器"""
    print("\n" + "="*60)
    print("测试训练计划模板补充器")
    print("="*60)
    
    # 加载模块
    module_path = project_root / "src/applications/fitness/data_supplement/workout_program_supplementer.py"
    module = load_module_from_file("workout_program_supplementer", module_path)
    
    # 创建补充器
    supplementer = module.WorkoutProgramSupplementer(
        neo4j_driver=None,
        data_dir="data/training_knowledge"
    )
    
    # 测试加载数据
    programs_data = supplementer._load_programs_data()
    assert 'programs' in programs_data
    assert len(programs_data['programs']) > 0
    print(f"✅ 成功加载训练计划模板数据: {len(programs_data['programs'])} 个计划")
    
    # 测试推断训练分化
    result = supplementer._infer_training_split({"workouts": {"A": {}, "B": {}}})
    assert result == "上下肢分化"
    print(f"✅ 推断训练分化测试通过: {result}")
    
    # 测试推断训练目标
    result = supplementer._infer_training_goal({"description": "A strength training program"})
    assert result == "力量提升"
    print(f"✅ 推断训练目标测试通过: {result}")
    
    print("✅ 训练计划模板补充器测试通过")


def test_acsm_standard_supplementer():
    """测试ACSM标准补充器"""
    print("\n" + "="*60)
    print("测试ACSM标准补充器")
    print("="*60)
    
    # 加载模块
    module_path = project_root / "src/applications/fitness/data_supplement/acsm_standard_supplementer.py"
    module = load_module_from_file("acsm_standard_supplementer", module_path)
    
    # 创建补充器
    supplementer = module.ACSMStandardSupplementer(
        neo4j_driver=None,
        data_dir="data/training_knowledge"
    )
    
    # 测试目录存在
    assert supplementer.standards_dir.exists()
    print(f"✅ ACSM标准目录存在: {supplementer.standards_dir}")
    
    # 测试生成ID
    standard_id = supplementer._generate_standard_id("fitt_principle_1_20251110_221821")
    assert standard_id == "acsm_std_fitt_principle_1_20251110_221821"
    print(f"✅ 生成ID测试通过: {standard_id}")
    
    # 测试翻译标题
    assert supplementer._translate_title("fitt_principle") == "FITT原则"
    print(f"✅ 翻译标题测试通过")
    
    print("✅ ACSM标准补充器测试通过")


def test_nsca_standard_supplementer():
    """测试NSCA标准补充器"""
    print("\n" + "="*60)
    print("测试NSCA标准补充器")
    print("="*60)
    
    # 加载模块
    module_path = project_root / "src/applications/fitness/data_supplement/nsca_standard_supplementer.py"
    module = load_module_from_file("nsca_standard_supplementer", module_path)
    
    # 创建补充器
    supplementer = module.NSCAStandardSupplementer(
        neo4j_driver=None,
        data_dir="data/training_knowledge"
    )
    
    # 测试目录存在
    assert supplementer.standards_dir.exists()
    print(f"✅ NSCA标准目录存在: {supplementer.standards_dir}")
    
    # 测试生成ID
    standard_id = supplementer._generate_standard_id("strength_essentials_0_20251110_221821")
    assert standard_id == "nsca_std_strength_essentials_0_20251110_221821"
    print(f"✅ 生成ID测试通过: {standard_id}")
    
    # 测试翻译标题
    assert supplementer._translate_title("strength_essentials") == "力量训练基础"
    print(f"✅ 翻译标题测试通过")
    
    print("✅ NSCA标准补充器测试通过")


def main():
    """运行所有测试"""
    print("\n" + "="*60)
    print("开始测试训练知识导入器")
    print("="*60)
    
    try:
        test_training_volume_supplementer()
        test_strength_standard_supplementer()
        test_workout_program_supplementer()
        test_acsm_standard_supplementer()
        test_nsca_standard_supplementer()
        
        print("\n" + "="*60)
        print("✅ 所有测试通过！")
        print("="*60)
        return 0
    
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
