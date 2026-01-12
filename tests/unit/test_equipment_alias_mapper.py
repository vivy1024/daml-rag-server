# -*- coding: utf-8 -*-
"""
器械别名映射器单元测试

测试EquipmentAliasMapper服务类的功能
Requirements: 4.1, 4.2, 4.3
"""

import pytest
import os
import tempfile
import yaml
from unittest.mock import patch

from src.applications.fitness.services.equipment_alias_mapper import (
    EquipmentAliasMapper,
    get_equipment_alias_mapper,
    reset_equipment_alias_mapper
)


class TestEquipmentAliasMapper:
    """器械别名映射器测试类"""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """每个测试前重置单例"""
        reset_equipment_alias_mapper()
        yield
        reset_equipment_alias_mapper()
    
    @pytest.fixture
    def mapper(self):
        """创建映射器实例"""
        return EquipmentAliasMapper()
    
    @pytest.fixture
    def custom_config_file(self):
        """创建自定义配置文件"""
        config = {
            "equipment_aliases": {
                "test_equipment": {
                    "english_name": "Test Equipment",
                    "chinese_aliases": ["测试器械", "测试设备"],
                    "description": "测试用器械",
                    "common_in_gyms": True,
                    "university_gym_available": True
                }
            },
            "university_gym_basic_equipment": ["测试器械"],
            "commercial_gym_standard_equipment": ["测试器械", "测试设备"]
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False, encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True)
            temp_path = f.name
        
        yield temp_path
        
        # 清理临时文件
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    # ==================== 基础映射测试 ====================
    
    def test_map_to_english_cable(self, mapper):
        """测试龙门架映射到Cable - Requirements: 4.1"""
        assert mapper.map_to_english("龙门架") == "Cable"
        assert mapper.map_to_english("绳索") == "Cable"
        assert mapper.map_to_english("拉力器") == "Cable"
        assert mapper.map_to_english("大飞鸟") == "Cable"
    
    def test_map_to_english_smith_machine(self, mapper):
        """测试史密斯机映射 - Requirements: 4.1"""
        assert mapper.map_to_english("史密斯机") == "Smith Machine"
        assert mapper.map_to_english("史密斯架") == "Smith Machine"
    
    def test_map_to_english_barbell(self, mapper):
        """测试杠铃映射 - Requirements: 4.1"""
        assert mapper.map_to_english("杠铃") == "Barbell"
        assert mapper.map_to_english("曲杆") == "Barbell"
        assert mapper.map_to_english("EZ杆") == "Barbell"
    
    def test_map_to_english_dumbbell(self, mapper):
        """测试哑铃映射 - Requirements: 4.1"""
        assert mapper.map_to_english("哑铃") == "Dumbbell"
        assert mapper.map_to_english("固定哑铃") == "Dumbbell"
    
    def test_map_to_english_machine(self, mapper):
        """测试固定器械映射 - Requirements: 4.1"""
        assert mapper.map_to_english("器械") == "Machine"
        assert mapper.map_to_english("固定器械") == "Machine"
        assert mapper.map_to_english("坐姿推胸机") == "Machine"
        assert mapper.map_to_english("高位下拉机") == "Machine"
    
    def test_map_to_english_body_weight(self, mapper):
        """测试自重训练映射 - Requirements: 4.1"""
        assert mapper.map_to_english("徒手") == "Body Weight"
        assert mapper.map_to_english("自重") == "Body Weight"
        assert mapper.map_to_english("无器械") == "Body Weight"
    
    def test_map_to_english_unknown(self, mapper):
        """测试未知器械返回原名称"""
        # 使用完全不匹配的名称
        assert mapper.map_to_english("完全未知的东西") == "完全未知的东西"
        assert mapper.map_to_english("") == ""
        assert mapper.map_to_english(None) is None
    
    # ==================== 列表映射测试 ====================
    
    def test_map_list_to_english(self, mapper):
        """测试列表映射"""
        chinese_list = ["杠铃", "哑铃", "龙门架"]
        english_list = mapper.map_list_to_english(chinese_list)
        
        assert "Barbell" in english_list
        assert "Dumbbell" in english_list
        assert "Cable" in english_list
    
    def test_map_list_to_english_dedup(self, mapper):
        """测试列表映射去重"""
        chinese_list = ["龙门架", "绳索", "拉力器"]  # 都映射到Cable
        english_list = mapper.map_list_to_english(chinese_list)
        
        assert len(english_list) == 1
        assert english_list[0] == "Cable"
    
    def test_map_list_to_english_empty(self, mapper):
        """测试空列表映射"""
        assert mapper.map_list_to_english([]) == []
        assert mapper.map_list_to_english(None) == []
    
    # ==================== 反向映射测试 ====================
    
    def test_get_chinese_display_name(self, mapper):
        """测试获取中文显示名称 - Requirements: 4.2"""
        # 返回第一个别名
        assert mapper.get_chinese_display_name("Cable") == "龙门架"
        assert mapper.get_chinese_display_name("Barbell") == "杠铃"
        assert mapper.get_chinese_display_name("Dumbbell") == "哑铃"
    
    def test_get_chinese_display_name_unknown(self, mapper):
        """测试未知英文名称返回原名称"""
        assert mapper.get_chinese_display_name("Unknown") == "Unknown"
        assert mapper.get_chinese_display_name("") == ""
    
    def test_get_all_chinese_aliases(self, mapper):
        """测试获取所有中文别名"""
        aliases = mapper.get_all_chinese_aliases("Cable")
        
        assert "龙门架" in aliases
        assert "绳索" in aliases
        assert "拉力器" in aliases
    
    # ==================== 大学健身房配置测试 ====================
    
    def test_get_university_gym_equipment(self, mapper):
        """测试获取大学健身房基础配置 - Requirements: 4.3"""
        equipment = mapper.get_university_gym_equipment()
        
        assert len(equipment) > 0
        assert "哑铃" in equipment
        assert "杠铃" in equipment
    
    def test_get_university_gym_equipment_english(self, mapper):
        """测试获取大学健身房基础配置（英文）"""
        equipment = mapper.get_university_gym_equipment_english()
        
        assert len(equipment) > 0
        assert "Dumbbell" in equipment
        assert "Barbell" in equipment
    
    def test_is_equipment_available_in_university_gym(self, mapper):
        """测试检查器械是否在大学健身房配置中"""
        # 中文名称检查
        assert mapper.is_equipment_available_in_university_gym("哑铃") == True
        assert mapper.is_equipment_available_in_university_gym("杠铃") == True
        
        # 英文名称检查
        assert mapper.is_equipment_available_in_university_gym("Dumbbell") == True
    
    # ==================== 商业健身房配置测试 ====================
    
    def test_get_commercial_gym_equipment(self, mapper):
        """测试获取商业健身房标准配置"""
        equipment = mapper.get_commercial_gym_equipment()
        
        assert len(equipment) > 0
        assert "哑铃" in equipment
        assert "杠铃" in equipment
    
    # ==================== 动作过滤测试 ====================
    
    def test_filter_exercises_by_equipment(self, mapper):
        """测试根据可用器械过滤动作"""
        exercises = [
            {"name": "杠铃卧推", "equipment_zh": ["杠铃", "卧推凳"]},
            {"name": "哑铃飞鸟", "equipment_zh": ["哑铃", "卧推凳"]},
            {"name": "龙门架夹胸", "equipment_zh": ["龙门架"]},
            {"name": "俯卧撑", "equipment_zh": []},  # 自重训练
        ]
        
        # 只有杠铃和哑铃
        available = ["杠铃", "哑铃", "卧推凳"]
        filtered = mapper.filter_exercises_by_equipment(exercises, available)
        
        assert len(filtered) == 3  # 杠铃卧推、哑铃飞鸟、俯卧撑
        names = [e["name"] for e in filtered]
        assert "杠铃卧推" in names
        assert "哑铃飞鸟" in names
        assert "俯卧撑" in names
        assert "龙门架夹胸" not in names
    
    def test_filter_exercises_by_equipment_empty_available(self, mapper):
        """测试空可用器械列表返回所有动作"""
        exercises = [
            {"name": "杠铃卧推", "equipment_zh": ["杠铃"]},
            {"name": "哑铃飞鸟", "equipment_zh": ["哑铃"]},
        ]
        
        filtered = mapper.filter_exercises_by_equipment(exercises, [])
        assert len(filtered) == 2
    
    # ==================== 器械信息测试 ====================
    
    def test_get_equipment_info(self, mapper):
        """测试获取器械详细信息"""
        info = mapper.get_equipment_info("龙门架")
        
        assert info is not None
        assert info["english_name"] == "Cable"
        assert "龙门架" in info["chinese_aliases"]
    
    def test_get_equipment_info_by_english(self, mapper):
        """测试通过英文名获取器械信息"""
        info = mapper.get_equipment_info("Cable")
        
        assert info is not None
        assert info["english_name"] == "Cable"
    
    def test_get_equipment_info_unknown(self, mapper):
        """测试未知器械返回None"""
        # 使用完全不匹配的名称
        info = mapper.get_equipment_info("完全未知的东西")
        assert info is None
    
    # ==================== 用户类型推荐测试 ====================
    
    def test_suggest_equipment_for_student(self, mapper):
        """测试学生用户推荐大学健身房配置"""
        equipment = mapper.suggest_equipment_for_user_type("student")
        
        assert len(equipment) > 0
        # 大学健身房配置
        assert "哑铃" in equipment
    
    def test_suggest_equipment_for_worker(self, mapper):
        """测试上班族用户推荐商业健身房配置"""
        equipment = mapper.suggest_equipment_for_user_type("worker")
        
        assert len(equipment) > 0
        # 商业健身房配置
        assert "哑铃" in equipment
    
    def test_suggest_equipment_for_other(self, mapper):
        """测试其他用户类型默认推荐商业健身房配置"""
        equipment = mapper.suggest_equipment_for_user_type("other")
        
        assert len(equipment) > 0
    
    # ==================== 自定义配置测试 ====================
    
    def test_custom_config_file(self, custom_config_file):
        """测试自定义配置文件加载"""
        mapper = EquipmentAliasMapper(config_path=custom_config_file)
        
        assert mapper.map_to_english("测试器械") == "Test Equipment"
        assert mapper.map_to_english("测试设备") == "Test Equipment"
    
    # ==================== 单例模式测试 ====================
    
    def test_singleton_pattern(self):
        """测试单例模式"""
        mapper1 = get_equipment_alias_mapper()
        mapper2 = get_equipment_alias_mapper()
        
        assert mapper1 is mapper2
    
    def test_reset_singleton(self):
        """测试重置单例"""
        mapper1 = get_equipment_alias_mapper()
        reset_equipment_alias_mapper()
        mapper2 = get_equipment_alias_mapper()
        
        assert mapper1 is not mapper2


class TestEquipmentAliasMappingCompleteness:
    """测试器械别名映射的完整性"""
    
    @pytest.fixture
    def mapper(self):
        """创建映射器实例"""
        reset_equipment_alias_mapper()
        return EquipmentAliasMapper()
    
    def test_common_chinese_gym_equipment_mapped(self, mapper):
        """测试常见中国健身房器械都有映射"""
        common_equipment = [
            "龙门架", "史密斯机", "杠铃", "哑铃", "壶铃",
            "器械", "固定器械", "徒手", "自重",
            "卧推凳", "单杠", "双杠", "弹力带", "瑜伽球"
        ]
        
        for equipment in common_equipment:
            english = mapper.map_to_english(equipment)
            # 确保映射到了英文名称（不是返回原名称）
            assert english != equipment or equipment in ["器械"], \
                f"器械 '{equipment}' 没有正确映射"
    
    def test_all_mappings_have_reverse(self, mapper):
        """测试所有映射都有反向映射"""
        # 获取所有英文名称
        english_names = set()
        for alias in mapper._alias_to_english.values():
            english_names.add(alias)
        
        # 检查每个英文名称都有中文别名
        for english in english_names:
            aliases = mapper.get_all_chinese_aliases(english)
            assert len(aliases) > 0, f"英文名称 '{english}' 没有中文别名"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
