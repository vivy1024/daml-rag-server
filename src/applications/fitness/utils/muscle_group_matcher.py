"""
肌群名称模糊匹配器

支持中文肌群名称的模糊匹配，解决用户输入与数据库名称不一致的问题。
当数据库查询失败时，提供基于经验的默认训练量建议。

功能特性：
- 支持中文肌群名称别名映射
- 支持模糊匹配（包含匹配、拼音匹配等）
- 提供默认训练量建议（MEV/MAV/MRV）

作者: BUILD_BODY Team
版本: v1.0.0
需求: 5.1, 5.2, 5.3
"""

import logging
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class MuscleGroupMatcher:
    """
    肌群名称模糊匹配器
    
    用于将用户输入的肌群名称匹配到数据库中的标准名称。
    支持别名映射、模糊匹配和默认值返回。
    """
    
    # 肌群名称映射表
    # 键: Neo4j中的Muscle节点name_zh（与Exercise.primary_muscle_zh一致）
    # 值: 别名列表（用户可能输入的各种名称，包括解剖学标准名称）
    # 
    # 重要：v8.70.0后Neo4j Muscle节点使用Exercise.primary_muscle_zh命名
    # 需要将解剖学名称（如"腘绳肌"）映射到实际节点名称（如"腿后肌群"）
    MUSCLE_GROUP_ALIASES: Dict[str, List[str]] = {
        # === 胸部肌群 ===
        "胸部": ["胸肌", "胸大肌", "胸", "chest", "pectoralis", "pec", "pecs", "大胸肌"],
        "上胸": ["上胸肌", "锁骨部胸肌", "upper chest"],
        "中胸与下胸": ["中胸", "下胸", "胸骨部胸肌", "mid chest", "lower chest"],
        
        # === 背部肌群 ===
        "背阔肌": ["背肌", "背部", "背", "back", "latissimus", "lat", "lats", "大背肌"],
        "下背部": ["竖脊肌", "下背", "腰部", "erector spinae", "erector", "lower back", "腰"],
        "斜方肌": ["斜方", "trapezius", "trap", "traps"],
        "斜方肌（中背）": ["中斜方肌", "中背", "菱形肌", "rhomboid", "mid back"],
        "上斜方肌": ["上斜方", "upper trapezius", "上背"],
        "斜方肌下部": ["下斜方肌", "lower trapezius"],
        
        # === 肩部肌群 ===
        "三角肌前束": ["前三角", "前束", "anterior deltoid", "front delt", "前肩"],
        "三角肌中束": ["中三角", "中束", "lateral deltoid", "side delt", "侧肩"],
        "三角肌后束": ["后三角", "后束", "posterior deltoid", "rear delt", "后肩"],
        "肩部": ["三角肌", "肩膀", "肩", "deltoid", "delt", "delts", "shoulder", "shoulders"],
        
        # === 手臂肌群 ===
        "肱二头肌": ["二头肌", "二头", "biceps", "bicep", "上臂前侧"],
        "肱二头肌长头": ["二头长头", "biceps long head"],
        "肱二头肌短头": ["二头短头", "biceps short head"],
        "肱三头肌": ["三头肌", "三头", "triceps", "tricep", "上臂后侧"],
        "肱三头肌外侧头": ["三头外侧头", "triceps lateral head"],
        "三头肌长头": ["三头长头", "triceps long head"],
        "前臂肌群": ["前臂", "前臂屈肌", "前臂伸肌", "forearm", "forearms"],
        "腕伸肌群": ["腕伸肌", "wrist extensors"],
        
        # === 腿部肌群 ===
        "股四头肌": ["大腿前侧", "股四", "quadriceps", "quad", "quads", "大腿前", "前腿"],
        "股四头肌内侧": ["股内侧肌", "vastus medialis", "VMO"],
        "股直肌": ["rectus femoris"],
        "腿后肌群": ["腘绳肌", "大腿后侧", "hamstrings", "hamstring", "hams", "大腿后", "后腿"],
        "腘绳肌内侧": ["半腱肌", "半膜肌", "medial hamstrings"],
        "股二头肌（外侧）": ["股二头肌", "biceps femoris", "外侧腘绳肌"],
        "臀部": ["臀大肌", "臀肌", "臀", "gluteus maximus", "glute", "glutes", "屁股"],
        "臀中肌": ["臀中", "gluteus medius"],
        "大腿内侧": ["内收肌群", "内收肌", "adductors", "adductor", "内侧"],
        "小腿": ["腓肠肌", "小腿肌", "calf", "calves", "gastrocnemius", "小腿后侧"],
        "胫骨前肌": ["胫前肌", "小腿前侧", "tibialis anterior"],
        "双脚": ["足部", "脚", "feet", "foot"],
        
        # === 核心肌群 ===
        "腹直肌": ["腹肌", "腹部", "腹", "abs", "abdominals", "rectus abdominis", "六块肌"],
        "上腹肌": ["上腹", "upper abs"],
        "下腹部": ["下腹", "下腹肌", "lower abs"],
        "腹斜肌": ["腹外斜肌", "腹内斜肌", "外斜肌", "内斜肌", "侧腹", "obliques"],
        "腹股沟": ["髂腰肌", "髋屈肌", "iliopsoas", "hip flexor", "hip flexors"],
        
        # === 颈部 ===
        "颈部": ["颈肌", "neck", "颈"],
        
        # === 未知/其他 ===
        "未知": ["其他", "unknown", "other"],
    }
    
    # 肌群分组映射（用于按组查询）
    # 使用Neo4j中的实际Muscle节点名称
    MUSCLE_GROUP_CATEGORIES: Dict[str, List[str]] = {
        "胸": ["胸部", "上胸", "中胸与下胸"],
        "背": ["背阔肌", "下背部", "斜方肌", "斜方肌（中背）", "上斜方肌", "斜方肌下部"],
        "肩": ["肩部", "三角肌前束", "三角肌中束", "三角肌后束"],
        "手臂": ["肱二头肌", "肱二头肌长头", "肱二头肌短头", "肱三头肌", "肱三头肌外侧头", "三头肌长头", "前臂肌群", "腕伸肌群"],
        "腿": ["股四头肌", "股四头肌内侧", "股直肌", "腿后肌群", "腘绳肌内侧", "股二头肌（外侧）", "臀部", "臀中肌", "大腿内侧", "小腿", "胫骨前肌", "双脚"],
        "核心": ["腹直肌", "上腹肌", "下腹部", "腹斜肌", "腹股沟"],
        "颈": ["颈部"],
    }
    
    # 默认训练量建议（基于Renaissance Periodization理论）
    # 键: Neo4j中的Muscle节点name_zh
    # 单位：组/周
    DEFAULT_VOLUME: Dict[str, Dict[str, int]] = {
        # === 胸部肌群 ===
        "胸部": {"mev": 10, "mav": 18, "mrv": 22},
        "上胸": {"mev": 6, "mav": 14, "mrv": 18},
        "中胸与下胸": {"mev": 8, "mav": 16, "mrv": 20},
        
        # === 背部肌群 ===
        "背阔肌": {"mev": 10, "mav": 18, "mrv": 25},
        "下背部": {"mev": 6, "mav": 12, "mrv": 18},
        "斜方肌": {"mev": 0, "mav": 12, "mrv": 20},
        "斜方肌（中背）": {"mev": 6, "mav": 14, "mrv": 20},
        "上斜方肌": {"mev": 0, "mav": 8, "mrv": 14},
        "斜方肌下部": {"mev": 6, "mav": 12, "mrv": 18},
        
        # === 肩部肌群 ===
        "肩部": {"mev": 8, "mav": 16, "mrv": 22},
        "三角肌前束": {"mev": 0, "mav": 8, "mrv": 14},
        "三角肌中束": {"mev": 8, "mav": 16, "mrv": 22},
        "三角肌后束": {"mev": 8, "mav": 16, "mrv": 22},
        
        # === 手臂肌群 ===
        "肱二头肌": {"mev": 8, "mav": 14, "mrv": 20},
        "肱二头肌长头": {"mev": 6, "mav": 12, "mrv": 18},
        "肱二头肌短头": {"mev": 6, "mav": 12, "mrv": 18},
        "肱三头肌": {"mev": 6, "mav": 12, "mrv": 18},
        "肱三头肌外侧头": {"mev": 4, "mav": 10, "mrv": 14},
        "三头肌长头": {"mev": 6, "mav": 12, "mrv": 16},
        "前臂肌群": {"mev": 4, "mav": 10, "mrv": 16},
        "腕伸肌群": {"mev": 4, "mav": 8, "mrv": 12},
        
        # === 腿部肌群 ===
        "股四头肌": {"mev": 8, "mav": 16, "mrv": 20},
        "股四头肌内侧": {"mev": 6, "mav": 12, "mrv": 16},
        "股直肌": {"mev": 6, "mav": 12, "mrv": 16},
        "腿后肌群": {"mev": 6, "mav": 12, "mrv": 16},
        "腘绳肌内侧": {"mev": 6, "mav": 10, "mrv": 14},
        "股二头肌（外侧）": {"mev": 6, "mav": 10, "mrv": 14},
        "臀部": {"mev": 4, "mav": 12, "mrv": 16},
        "臀中肌": {"mev": 4, "mav": 10, "mrv": 14},
        "大腿内侧": {"mev": 4, "mav": 10, "mrv": 14},
        "小腿": {"mev": 8, "mav": 12, "mrv": 16},
        "胫骨前肌": {"mev": 4, "mav": 8, "mrv": 12},
        "双脚": {"mev": 2, "mav": 6, "mrv": 10},
        
        # === 核心肌群 ===
        "腹直肌": {"mev": 0, "mav": 16, "mrv": 25},
        "上腹肌": {"mev": 0, "mav": 12, "mrv": 20},
        "下腹部": {"mev": 0, "mav": 12, "mrv": 20},
        "腹斜肌": {"mev": 0, "mav": 12, "mrv": 18},
        "腹股沟": {"mev": 4, "mav": 8, "mrv": 12},
        
        # === 颈部 ===
        "颈部": {"mev": 4, "mav": 8, "mrv": 12},
        
        # === 未知/其他 ===
        "未知": {"mev": 6, "mav": 12, "mrv": 18},
        
        # 通用默认值（用于未知肌群）
        "_default": {"mev": 6, "mav": 12, "mrv": 18},
    }
    
    def __init__(self):
        """初始化匹配器，构建反向索引"""
        self._build_reverse_index()
    
    def _build_reverse_index(self) -> None:
        """构建别名到标准名称的反向索引"""
        self._alias_to_standard: Dict[str, str] = {}
        
        for standard_name, aliases in self.MUSCLE_GROUP_ALIASES.items():
            # 标准名称本身也加入索引
            self._alias_to_standard[standard_name.lower()] = standard_name
            
            # 所有别名加入索引
            for alias in aliases:
                self._alias_to_standard[alias.lower()] = standard_name
        
        logger.debug(f"构建肌群名称索引完成，共{len(self._alias_to_standard)}个条目")
    
    def match(self, input_name: str) -> Optional[str]:
        """
        模糊匹配肌群名称
        
        匹配策略（按优先级）：
        1. 精确匹配（忽略大小写）
        2. 别名匹配
        3. 包含匹配（输入包含标准名称或别名）
        4. 部分匹配（标准名称或别名包含输入）
        
        Args:
            input_name: 用户输入的肌群名称
        
        Returns:
            标准肌群名称，如果无法匹配则返回None
        """
        if not input_name:
            return None
        
        input_lower = input_name.lower().strip()
        
        # 1. 精确匹配（包括别名）
        if input_lower in self._alias_to_standard:
            matched = self._alias_to_standard[input_lower]
            logger.debug(f"肌群名称精确匹配: '{input_name}' -> '{matched}'")
            return matched
        
        # 2. 包含匹配：输入包含标准名称或别名
        for alias, standard in self._alias_to_standard.items():
            if alias in input_lower:
                logger.debug(f"肌群名称包含匹配: '{input_name}' 包含 '{alias}' -> '{standard}'")
                return standard
        
        # 3. 部分匹配：标准名称或别名包含输入
        for alias, standard in self._alias_to_standard.items():
            if input_lower in alias:
                logger.debug(f"肌群名称部分匹配: '{alias}' 包含 '{input_name}' -> '{standard}'")
                return standard
        
        # 4. 无法匹配
        logger.warning(f"无法匹配肌群名称: '{input_name}'")
        return None
    
    def match_with_confidence(self, input_name: str) -> tuple[Optional[str], float]:
        """
        带置信度的模糊匹配
        
        Args:
            input_name: 用户输入的肌群名称
        
        Returns:
            (标准肌群名称, 置信度)，置信度范围0-1
        """
        if not input_name:
            return None, 0.0
        
        input_lower = input_name.lower().strip()
        
        # 精确匹配
        if input_lower in self._alias_to_standard:
            return self._alias_to_standard[input_lower], 1.0
        
        # 包含匹配
        for alias, standard in self._alias_to_standard.items():
            if alias in input_lower:
                # 计算置信度：别名长度/输入长度
                confidence = len(alias) / len(input_lower)
                return standard, min(confidence, 0.9)
        
        # 部分匹配
        for alias, standard in self._alias_to_standard.items():
            if input_lower in alias:
                # 计算置信度：输入长度/别名长度
                confidence = len(input_lower) / len(alias)
                return standard, min(confidence, 0.8)
        
        return None, 0.0
    
    def get_default_volume(self, muscle_group: str) -> Dict[str, int]:
        """
        获取默认训练量建议
        
        当数据库查询失败时，返回基于经验的默认训练量。
        
        Args:
            muscle_group: 肌群名称（可以是用户输入或标准名称）
        
        Returns:
            包含mev、mav、mrv的字典
        """
        # 尝试匹配到标准名称
        standard_name = self.match(muscle_group)
        
        if standard_name and standard_name in self.DEFAULT_VOLUME:
            volume = self.DEFAULT_VOLUME[standard_name]
            logger.info(f"返回肌群 '{standard_name}' 的默认训练量: {volume}")
            return volume
        
        # 返回通用默认值
        default = self.DEFAULT_VOLUME["_default"]
        logger.info(f"返回通用默认训练量（肌群: '{muscle_group}'）: {default}")
        return default
    
    def get_all_standard_names(self) -> List[str]:
        """获取所有标准肌群名称"""
        return list(self.MUSCLE_GROUP_ALIASES.keys())
    
    def get_muscles_by_category(self, category: str) -> List[str]:
        """
        按分类获取肌群列表
        
        Args:
            category: 分类名称（如"胸"、"背"、"腿"等）
        
        Returns:
            该分类下的肌群名称列表
        """
        category_lower = category.lower().strip()
        
        for cat_name, muscles in self.MUSCLE_GROUP_CATEGORIES.items():
            if cat_name == category_lower or category_lower in cat_name:
                return muscles
        
        return []
    
    def suggest_similar(self, input_name: str, max_suggestions: int = 3) -> List[str]:
        """
        建议相似的肌群名称
        
        当无法精确匹配时，返回可能的建议。
        
        Args:
            input_name: 用户输入的肌群名称
            max_suggestions: 最大建议数量
        
        Returns:
            相似肌群名称列表
        """
        if not input_name:
            return []
        
        input_lower = input_name.lower().strip()
        suggestions = []
        
        # 查找包含输入字符的标准名称
        for standard_name in self.MUSCLE_GROUP_ALIASES.keys():
            if any(char in standard_name for char in input_lower):
                suggestions.append(standard_name)
                if len(suggestions) >= max_suggestions:
                    break
        
        return suggestions


# 模块级别的单例实例
_matcher_instance: Optional[MuscleGroupMatcher] = None


def get_muscle_group_matcher() -> MuscleGroupMatcher:
    """获取肌群名称匹配器的单例实例"""
    global _matcher_instance
    if _matcher_instance is None:
        _matcher_instance = MuscleGroupMatcher()
    return _matcher_instance
