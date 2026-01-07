"""
中国健身房器械别名映射服务

版本: 1.0.0
更新日期: 2025-12-26

功能说明:
- 将中国健身房常用的器械名称映射到MuscleWiki英文名称
- 不修改Neo4j数据库，仅在代码层面添加别名映射
- 支持大学健身房基础配置模板

Requirements: 4.1, 4.2, 4.3
"""

import os
import yaml
import logging
from typing import Dict, List, Optional, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class EquipmentAliasMapper:
    """中国健身房器械别名映射服务"""
    
    # 默认配置文件路径
    DEFAULT_CONFIG_PATH = "config/equipment_alias_config.yaml"
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化器械别名映射器
        
        Args:
            config_path: 配置文件路径，默认使用DEFAULT_CONFIG_PATH
        """
        self._config_path = config_path or self._get_default_config_path()
        self._config: Dict = {}
        self._alias_to_english: Dict[str, str] = {}
        self._english_to_aliases: Dict[str, List[str]] = {}
        self._university_equipment: Set[str] = set()
        self._commercial_equipment: Set[str] = set()
        
        self._load_config()
        self._build_mappings()
    
    def _get_default_config_path(self) -> str:
        """获取默认配置文件路径"""
        # 尝试多个可能的路径
        possible_paths = [
            # 相对于当前工作目录
            self.DEFAULT_CONFIG_PATH,
            # 相对于daml-rag-server目录
            os.path.join("daml-rag-server", self.DEFAULT_CONFIG_PATH),
            # 相对于src目录向上查找
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                self.DEFAULT_CONFIG_PATH
            ),
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # 如果都不存在，返回默认路径（会在加载时使用内置映射）
        return self.DEFAULT_CONFIG_PATH
    
    def _load_config(self) -> None:
        """加载配置文件"""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"成功加载器械别名配置: {self._config_path}")
            else:
                logger.warning(f"配置文件不存在: {self._config_path}，使用内置默认映射")
                self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用内置默认映射")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取内置默认配置"""
        return {
            "equipment_aliases": {
                "cable": {
                    "english_name": "Cable",
                    "chinese_aliases": ["龙门架", "绳索", "拉力器", "大飞鸟", "小飞鸟"]
                },
                "smith_machine": {
                    "english_name": "Smith Machine",
                    "chinese_aliases": ["史密斯机", "史密斯架", "固定杠铃架"]
                },
                "barbell": {
                    "english_name": "Barbell",
                    "chinese_aliases": ["杠铃", "奥林匹克杠铃", "标准杠铃", "曲杆", "EZ杆"]
                },
                "dumbbell": {
                    "english_name": "Dumbbell",
                    "chinese_aliases": ["哑铃", "可调节哑铃", "固定哑铃"]
                },
                "kettlebell": {
                    "english_name": "Kettlebell",
                    "chinese_aliases": ["壶铃", "俄式壶铃"]
                },
                "machine": {
                    "english_name": "Machine",
                    "chinese_aliases": ["器械", "固定器械", "坐姿推胸机", "高位下拉机", "腿举机", "蝴蝶机"]
                },
                "body_weight": {
                    "english_name": "Body Weight",
                    "chinese_aliases": ["徒手", "自重", "无器械", "自身体重"]
                },
                "bench": {
                    "english_name": "Bench",
                    "chinese_aliases": ["卧推凳", "训练凳", "可调节凳", "平板凳"]
                },
                "pull_up_bar": {
                    "english_name": "Pull-up Bar",
                    "chinese_aliases": ["引体向上杆", "单杠", "引体杆"]
                },
                "dip_station": {
                    "english_name": "Dip Station",
                    "chinese_aliases": ["双杠", "臂屈伸架"]
                },
                "resistance_band": {
                    "english_name": "Resistance Band",
                    "chinese_aliases": ["弹力带", "阻力带", "拉力带"]
                },
                "exercise_ball": {
                    "english_name": "Exercise Ball",
                    "chinese_aliases": ["瑜伽球", "健身球", "稳定球"]
                }
            },
            "university_gym_basic_equipment": [
                "哑铃", "杠铃", "卧推凳", "单杠", "双杠", 
                "龙门架", "史密斯机", "固定器械", "跑步机"
            ],
            "commercial_gym_standard_equipment": [
                "哑铃", "杠铃", "壶铃", "卧推凳", "单杠", "双杠",
                "龙门架", "史密斯机", "固定器械", "跑步机", "划船机"
            ]
        }
    
    def _build_mappings(self) -> None:
        """构建映射字典"""
        equipment_aliases = self._config.get("equipment_aliases", {})
        
        for key, value in equipment_aliases.items():
            english_name = value.get("english_name", "")
            chinese_aliases = value.get("chinese_aliases", [])
            
            if english_name:
                # 构建中文到英文的映射
                for alias in chinese_aliases:
                    self._alias_to_english[alias] = english_name
                
                # 构建英文到中文别名列表的映射
                self._english_to_aliases[english_name] = chinese_aliases
        
        # 加载大学健身房配置
        university_equipment = self._config.get("university_gym_basic_equipment", [])
        self._university_equipment = set(university_equipment)
        
        # 加载商业健身房配置
        commercial_equipment = self._config.get("commercial_gym_standard_equipment", [])
        self._commercial_equipment = set(commercial_equipment)
        
        logger.info(f"构建器械别名映射完成: {len(self._alias_to_english)} 个中文别名")
    
    def map_to_english(self, chinese_name: str) -> str:
        """
        将中文器械名映射到英文
        
        Args:
            chinese_name: 中文器械名称
            
        Returns:
            对应的英文名称，如果没有映射则返回原名称
            
        Requirements: 4.1
        """
        if not chinese_name:
            return chinese_name
        
        # 直接查找映射
        if chinese_name in self._alias_to_english:
            return self._alias_to_english[chinese_name]
        
        # 尝试模糊匹配（包含关系）
        for alias, english in self._alias_to_english.items():
            if alias in chinese_name or chinese_name in alias:
                return english
        
        # 没有找到映射，返回原名称
        return chinese_name
    
    def map_list_to_english(self, chinese_names: List[str]) -> List[str]:
        """
        将中文器械名称列表映射到英文
        
        Args:
            chinese_names: 中文器械名称列表
            
        Returns:
            对应的英文名称列表（去重）
        """
        if not chinese_names:
            return []
        
        english_names = set()
        for name in chinese_names:
            english_name = self.map_to_english(name)
            english_names.add(english_name)
        
        return list(english_names)
    
    def get_chinese_display_name(self, english_name: str) -> str:
        """
        获取英文器械名称的中文显示名称
        
        Args:
            english_name: 英文器械名称
            
        Returns:
            中文显示名称（返回第一个别名），如果没有映射则返回原名称
            
        Requirements: 4.2
        """
        if not english_name:
            return english_name
        
        aliases = self._english_to_aliases.get(english_name, [])
        if aliases:
            return aliases[0]  # 返回第一个别名作为显示名称
        
        return english_name
    
    def get_all_chinese_aliases(self, english_name: str) -> List[str]:
        """
        获取英文器械名称的所有中文别名
        
        Args:
            english_name: 英文器械名称
            
        Returns:
            所有中文别名列表
        """
        return self._english_to_aliases.get(english_name, [])
    
    def get_university_gym_equipment(self) -> List[str]:
        """
        获取大学健身房基础配置器械列表
        
        Returns:
            大学健身房基础器械列表（中文）
            
        Requirements: 4.3
        """
        return list(self._university_equipment)
    
    def get_university_gym_equipment_english(self) -> List[str]:
        """
        获取大学健身房基础配置器械列表（英文）
        
        Returns:
            大学健身房基础器械列表（英文）
        """
        return self.map_list_to_english(list(self._university_equipment))
    
    def get_commercial_gym_equipment(self) -> List[str]:
        """
        获取商业健身房标准配置器械列表
        
        Returns:
            商业健身房标准器械列表（中文）
        """
        return list(self._commercial_equipment)
    
    def get_commercial_gym_equipment_english(self) -> List[str]:
        """
        获取商业健身房标准配置器械列表（英文）
        
        Returns:
            商业健身房标准器械列表（英文）
        """
        return self.map_list_to_english(list(self._commercial_equipment))
    
    def is_equipment_available_in_university_gym(self, equipment_name: str) -> bool:
        """
        检查器械是否在大学健身房基础配置中
        
        Args:
            equipment_name: 器械名称（中文或英文）
            
        Returns:
            是否在大学健身房基础配置中
        """
        # 检查中文名称
        if equipment_name in self._university_equipment:
            return True
        
        # 检查英文名称（转换为中文后检查）
        chinese_name = self.get_chinese_display_name(equipment_name)
        return chinese_name in self._university_equipment
    
    def filter_exercises_by_equipment(
        self, 
        exercises: List[Dict], 
        available_equipment: List[str],
        equipment_field: str = "equipment_zh"
    ) -> List[Dict]:
        """
        根据可用器械过滤动作列表
        
        Args:
            exercises: 动作列表
            available_equipment: 可用器械列表（中文）
            equipment_field: 动作中器械字段名
            
        Returns:
            过滤后的动作列表
        """
        if not available_equipment:
            return exercises
        
        # 将可用器械转换为英文集合
        available_english = set(self.map_list_to_english(available_equipment))
        
        filtered = []
        for exercise in exercises:
            exercise_equipment = exercise.get(equipment_field, [])
            if isinstance(exercise_equipment, str):
                exercise_equipment = [exercise_equipment]
            
            # 将动作器械转换为英文
            exercise_equipment_english = set(self.map_list_to_english(exercise_equipment))
            
            # 检查是否有交集（动作所需器械是否在可用器械中）
            if exercise_equipment_english & available_english:
                filtered.append(exercise)
            elif not exercise_equipment:
                # 无器械要求的动作（如自重训练）
                filtered.append(exercise)
        
        return filtered
    
    def get_equipment_info(self, equipment_name: str) -> Optional[Dict]:
        """
        获取器械的详细信息
        
        Args:
            equipment_name: 器械名称（中文或英文）
            
        Returns:
            器械信息字典，包含英文名、中文别名、描述等
        """
        equipment_aliases = self._config.get("equipment_aliases", {})
        
        # 先尝试通过中文名查找
        english_name = self.map_to_english(equipment_name)
        
        # 在配置中查找对应的器械信息
        for key, value in equipment_aliases.items():
            if value.get("english_name") == english_name:
                return {
                    "key": key,
                    "english_name": value.get("english_name"),
                    "chinese_aliases": value.get("chinese_aliases", []),
                    "description": value.get("description", ""),
                    "common_in_gyms": value.get("common_in_gyms", True),
                    "university_gym_available": value.get("university_gym_available", False)
                }
        
        return None
    
    def suggest_equipment_for_user_type(self, user_type: str) -> List[str]:
        """
        根据用户类型推荐器械配置
        
        Args:
            user_type: 用户类型 (student/worker/other)
            
        Returns:
            推荐的器械列表（中文）
        """
        if user_type == "student":
            return self.get_university_gym_equipment()
        elif user_type == "worker":
            return self.get_commercial_gym_equipment()
        else:
            # 默认返回商业健身房配置
            return self.get_commercial_gym_equipment()


# 单例模式
_mapper_instance: Optional[EquipmentAliasMapper] = None


def get_equipment_alias_mapper(config_path: Optional[str] = None) -> EquipmentAliasMapper:
    """
    获取器械别名映射器单例
    
    Args:
        config_path: 配置文件路径（仅首次调用时有效）
        
    Returns:
        EquipmentAliasMapper实例
    """
    global _mapper_instance
    if _mapper_instance is None:
        _mapper_instance = EquipmentAliasMapper(config_path)
    return _mapper_instance


def reset_equipment_alias_mapper() -> None:
    """重置器械别名映射器单例（主要用于测试）"""
    global _mapper_instance
    _mapper_instance = None
