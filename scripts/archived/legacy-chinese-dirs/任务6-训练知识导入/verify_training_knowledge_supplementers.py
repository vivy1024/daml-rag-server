"""
验证训练知识导入器代码

检查所有补充器文件的语法和基本结构
"""

import ast
import sys
from pathlib import Path

# 项目根目录
project_root = Path(__file__).parent.parent


def verify_python_file(file_path: Path) -> bool:
    """
    验证Python文件的语法
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否验证通过
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 解析AST
        ast.parse(code)
        
        print(f"✅ {file_path.name}: 语法正确")
        return True
    
    except SyntaxError as e:
        print(f"❌ {file_path.name}: 语法错误 - {e}")
        return False
    except Exception as e:
        print(f"❌ {file_path.name}: 验证失败 - {e}")
        return False


def check_class_exists(file_path: Path, class_name: str) -> bool:
    """
    检查文件中是否存在指定的类
    
    Args:
        file_path: 文件路径
        class_name: 类名
        
    Returns:
        bool: 是否存在
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 解析AST
        tree = ast.parse(code)
        
        # 查找类定义
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                print(f"✅ {file_path.name}: 找到类 {class_name}")
                return True
        
        print(f"❌ {file_path.name}: 未找到类 {class_name}")
        return False
    
    except Exception as e:
        print(f"❌ {file_path.name}: 检查类失败 - {e}")
        return False


def check_method_exists(file_path: Path, class_name: str, method_name: str) -> bool:
    """
    检查类中是否存在指定的方法
    
    Args:
        file_path: 文件路径
        class_name: 类名
        method_name: 方法名
        
    Returns:
        bool: 是否存在
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
        
        # 解析AST
        tree = ast.parse(code)
        
        # 查找类定义
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                # 查找方法
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == method_name:
                        print(f"✅ {file_path.name}: 找到方法 {class_name}.{method_name}")
                        return True
        
        print(f"❌ {file_path.name}: 未找到方法 {class_name}.{method_name}")
        return False
    
    except Exception as e:
        print(f"❌ {file_path.name}: 检查方法失败 - {e}")
        return False


def main():
    """运行验证"""
    print("\n" + "="*60)
    print("验证训练知识导入器代码")
    print("="*60)
    
    # 定义要验证的文件和类
    supplementers = [
        {
            "file": "src/applications/fitness/data_supplement/training_volume_supplementer.py",
            "class": "TrainingVolumeSupplementer",
            "methods": ["supplement", "_load_volume_data", "_update_muscle_volume"]
        },
        {
            "file": "src/applications/fitness/data_supplement/strength_standard_supplementer.py",
            "class": "StrengthStandardSupplementer",
            "methods": ["supplement", "_load_standards_data", "_create_strength_standard"]
        },
        {
            "file": "src/applications/fitness/data_supplement/workout_program_supplementer.py",
            "class": "WorkoutProgramSupplementer",
            "methods": ["supplement", "_load_programs_data", "_create_workout_program"]
        },
        {
            "file": "src/applications/fitness/data_supplement/acsm_standard_supplementer.py",
            "class": "ACSMStandardSupplementer",
            "methods": ["supplement", "_load_standard_file", "_create_acsm_standard"]
        },
        {
            "file": "src/applications/fitness/data_supplement/nsca_standard_supplementer.py",
            "class": "NSCAStandardSupplementer",
            "methods": ["supplement", "_load_standard_file", "_create_nsca_standard"]
        }
    ]
    
    all_passed = True
    
    for supplementer in supplementers:
        print(f"\n{'='*60}")
        print(f"验证: {supplementer['class']}")
        print(f"{'='*60}")
        
        file_path = project_root / supplementer['file']
        
        # 1. 验证语法
        if not verify_python_file(file_path):
            all_passed = False
            continue
        
        # 2. 检查类存在
        if not check_class_exists(file_path, supplementer['class']):
            all_passed = False
            continue
        
        # 3. 检查方法存在
        for method in supplementer['methods']:
            if not check_method_exists(file_path, supplementer['class'], method):
                all_passed = False
    
    # 验证数据文件存在
    print(f"\n{'='*60}")
    print("验证数据文件")
    print(f"{'='*60}")
    
    data_files = [
        "data/training_knowledge/training-volume-landmarks.json",
        "data/training_knowledge/strength-standards.json",
        "data/training_knowledge/workout-programs.json",
        "data/training_knowledge/acsm_standards",
        "data/training_knowledge/nsca_standards"
    ]
    
    for data_file in data_files:
        file_path = project_root / data_file
        if file_path.exists():
            print(f"✅ {data_file}: 存在")
        else:
            print(f"❌ {data_file}: 不存在")
            all_passed = False
    
    # 总结
    print(f"\n{'='*60}")
    if all_passed:
        print("✅ 所有验证通过！")
        print("="*60)
        return 0
    else:
        print("❌ 部分验证失败")
        print("="*60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
