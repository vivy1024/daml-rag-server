"""
测试重构模块

验证 workflow 和 config 模块是否正常工作。
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_workflow_module():
    """测试 workflow 模块"""
    print("=" * 50)
    print("测试 workflow 模块")
    print("=" * 50)
    
    from src.applications.fitness.workflow import (
        WorkflowState,
        StateUpdate,
        WorkflowStep,
        ComplexityLevel,
        create_initial_state,
        serialize_state,
        deserialize_state,
    )
    
    # 测试创建初始状态
    state = create_initial_state(
        request_id='test-123',
        user_id='user-456',
        query_text='帮我制定一个增肌计划',
        domain='fitness'
    )
    print('✅ 创建初始状态成功')
    print(f'   request_id: {state["request_id"]}')
    print(f'   user_id: {state["user_id"]}')
    print(f'   query_text: {state["query_text"]}')
    
    # 测试状态更新
    update = StateUpdate(updates={'complexity_level': 'moderate'})
    new_state = update.merge_into(state)
    print(f'✅ 状态更新成功: complexity_level = {new_state["complexity_level"]}')
    
    # 测试带错误的状态更新
    update_with_error = StateUpdate(
        updates={'selected_model': 'deepseek-chat'},
        error='测试错误'
    )
    state_with_error = update_with_error.merge_into(new_state)
    print(f'✅ 带错误的状态更新成功: errors = {state_with_error["errors"]}')
    
    # 测试序列化
    serialized = serialize_state(state_with_error)
    print(f'✅ 序列化成功: type = {type(serialized).__name__}')
    
    # 测试反序列化
    restored = deserialize_state(serialized)
    print(f'✅ 反序列化成功: request_id = {restored["request_id"]}')
    
    # 测试枚举
    print(f'✅ WorkflowStep 枚举: {WorkflowStep.EXECUTE_DAG.value}')
    print(f'✅ ComplexityLevel 枚举: {ComplexityLevel.COMPLEX.value}')
    
    print()
    print('=== workflow 模块测试通过 ===')
    print()


def test_config_module():
    """测试 config 模块"""
    print("=" * 50)
    print("测试 config 模块")
    print("=" * 50)
    
    from src.applications.fitness.config import (
        FieldMappingManager,
        get_field_mapping_manager,
        map_exercise_fields,
        map_muscle_fields,
        batch_map_exercise_fields,
        batch_map_muscle_fields,
        EXERCISE_FIELD_MAPPING,
        MUSCLE_FIELD_MAPPING,
    )
    
    # 重置单例以确保测试独立
    FieldMappingManager.reset_instance()
    
    # 测试获取管理器实例
    manager = get_field_mapping_manager()
    print(f'✅ 获取 FieldMappingManager 实例成功')
    
    # 测试列出实体类型
    entity_types = manager.list_entity_types()
    print(f'✅ 实体类型: {entity_types}')
    
    # 测试 Neo4j -> MCP 映射
    neo4j_data = {
        'id': 'ex-001',
        'name': '卧推',
        'difficulty': 'intermediate',
        'force': 'push',
        'mechanic': 'compound',
    }
    mapped = manager.map_from_neo4j('exercise', neo4j_data)
    print(f'✅ Neo4j -> MCP 映射成功:')
    print(f'   exercise_id: {mapped.get("exercise_id")}')
    print(f'   difficulty_level: {mapped.get("difficulty_level")}')
    
    # 测试向后兼容函数
    mapped_compat = map_exercise_fields(neo4j_data)
    print(f'✅ 向后兼容函数 map_exercise_fields 成功')
    
    # 测试批量映射
    results = [neo4j_data, {'id': 'ex-002', 'name': '深蹲', 'difficulty': 'advanced'}]
    batch_mapped = batch_map_exercise_fields(results)
    print(f'✅ 批量映射成功: {len(batch_mapped)} 条记录')
    
    # 测试 MCP -> Neo4j 映射
    mcp_data = {
        'exercise_id': 'ex-003',
        'difficulty_level': 'beginner',
    }
    neo4j_mapped = manager.map_to_neo4j('exercise', mcp_data)
    print(f'✅ MCP -> Neo4j 映射成功:')
    print(f'   id: {neo4j_mapped.get("id")}')
    print(f'   difficulty: {neo4j_mapped.get("difficulty")}')
    
    # 测试动态添加映射
    manager.add_mapping('food', 'food_id', 'id')
    manager.add_mapping('food', 'food_name', 'name')
    food_data = {'id': 'food-001', 'name': '鸡胸肉'}
    food_mapped = manager.map_from_neo4j('food', food_data)
    print(f'✅ 动态添加映射成功: food_id = {food_mapped.get("food_id")}')
    
    print()
    print('=== config 模块测试通过 ===')
    print()


def test_backward_compatibility():
    """测试向后兼容性"""
    print("=" * 50)
    print("测试向后兼容性")
    print("=" * 50)
    
    # 测试从原有路径导入
    from src.applications.fitness.neo4j_field_mapping import (
        EXERCISE_FIELD_MAPPING,
        MUSCLE_FIELD_MAPPING,
        map_exercise_fields,
        map_muscle_fields,
        batch_map_exercise_fields,
        batch_map_muscle_fields,
    )
    
    print(f'✅ 从 neo4j_field_mapping 导入成功')
    print(f'   EXERCISE_FIELD_MAPPING keys: {list(EXERCISE_FIELD_MAPPING.keys())[:3]}...')
    print(f'   MUSCLE_FIELD_MAPPING keys: {list(MUSCLE_FIELD_MAPPING.keys())}')
    
    # 测试函数调用
    result = map_exercise_fields({'id': 'test', 'difficulty': 'easy'})
    print(f'✅ map_exercise_fields 调用成功')
    
    print()
    print('=== 向后兼容性测试通过 ===')
    print()


def main():
    """运行所有测试"""
    print()
    print("=" * 60)
    print("  重构模块测试")
    print("=" * 60)
    print()
    
    try:
        test_workflow_module()
        test_config_module()
        test_backward_compatibility()
        
        print("=" * 60)
        print("  ✅ 所有测试通过！")
        print("=" * 60)
        return 0
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
