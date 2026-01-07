#!/usr/bin/env python
"""Direct Tool Test"""

import sys
import os

# 直接导入工具模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'applications', 'fitness', 'tools'))

def test_direct_import():
    """Test direct tool import"""
    print("Testing direct tool import...")
    
    try:
        # 直接导入Python文件
        import intelligent_exercise_selector
        print("  [OK] intelligent_exercise_selector.py imported")
        
        # 检查类是否存在
        if hasattr(intelligent_exercise_selector, 'IntelligentExerciseSelector'):
            print("  [OK] IntelligentExerciseSelector class found")
            return True
        else:
            print("  [FAIL] IntelligentExerciseSelector class not found")
            return False
    except Exception as e:
        print(f"  [FAIL] Import error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_direct_import()
    sys.exit(0 if success else 1)
