"""
内容安全过滤服务

实现敏感词过滤和违规内容检测，确保生成内容符合合规要求。

版本: v1.0.0
创建日期: 2025-12-31
Requirements: 16.4
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ContentRiskLevel(Enum):
    """内容风险等级"""
    SAFE = "safe"           # 安全，可直接输出
    LOW = "low"             # 低风险，添加提示后输出
    MEDIUM = "medium"       # 中风险，添加警告后输出
    HIGH = "high"           # 高风险，需要人工审核
    BLOCKED = "blocked"     # 禁止，拒绝输出


class ContentCategory(Enum):
    """内容类别"""
    MEDICAL = "medical"             # 医疗相关
    DANGEROUS = "dangerous"         # 危险内容
    EXTREME = "extreme"             # 极端方法
    POLITICAL = "political"         # 政治敏感
    ILLEGAL = "illegal"             # 违法违规
    INAPPROPRIATE = "inappropriate" # 不当内容
    SELF_HARM = "self_harm"         # 自我伤害
    DANGEROUS_SUBSTANCE = "dangerous_substance"  # 危险物质


@dataclass
class FilterResult:
    """过滤结果"""
    risk_level: ContentRiskLevel
    categories: List[ContentCategory] = field(default_factory=list)
    matched_keywords: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    modified_content: Optional[str] = None
    should_block: bool = False
    requires_review: bool = False


class ContentSafetyFilter:
    """
    内容安全过滤器
    
    功能：
    1. 敏感词过滤
    2. 违规内容检测
    3. 医疗边界检测
    4. 危险内容检测
    5. 内容标识添加
    """
    
    def __init__(self):
        """初始化过滤器"""
        self._init_sensitive_words()
        self._init_patterns()
        self._init_disclaimers()
        logger.info("内容安全过滤器初始化完成")
    
    def _init_sensitive_words(self):
        """初始化敏感词库"""
        # 医疗越界词汇（medical_advice）
        self.medical_keywords = {
            # 诊断相关
            "诊断", "确诊", "病症", "疾病", "病情",
            "症状分析", "病理", "临床表现",
            # 治疗相关
            "治疗", "治愈", "康复治疗", "医治", "根治",
            "理疗", "针灸治疗",
            # 药物相关
            "药物", "用药", "服药", "处方", "药方",
            "止痛药", "消炎药", "抗生素", "激素",
            "布洛芬", "阿司匹林", "处方药",
            # 医疗建议
            "就医", "看医生", "挂号", "住院", "手术",
            "化验", "CT检查", "核磁共振",
        }

        # 自我伤害相关词汇（self_harm）
        self.self_harm_keywords = {
            "自残", "自伤", "割腕", "自杀", "轻生",
            "不想活", "活着没意思", "结束生命", "了断",
            "跳楼", "服毒", "过量服药", "厌世",
            "自我惩罚", "故意受伤", "伤害自己",
        }

        # 危险物质词汇（dangerous_substances）
        self.dangerous_substances_keywords = {
            "类固醇", "合成代谢类固醇", "睾酮注射",
            "生长激素", "HGH", "EPO", "促红细胞生成素",
            "兴奋剂", "安非他命", "麻黄碱",
            "利尿剂减重", "DNP", "二硝基苯酚",
            "西布曲明", "禁药", "违禁药物",
            "氯巴占", "美沙酮",
        }

        # 危险动作/方法词汇
        self.dangerous_keywords = {
            # 极端减肥
            "绝食", "断食超过", "催吐", "泻药减肥",
            "灌肠减肥", "裹保鲜膜减肥",
            # 危险训练
            "极限负重", "超负荷", "忽视疼痛", "带伤训练",
            "锁死关节", "颈后深蹲", "弹震式拉伸",
            # 违禁物质（保留兼容）
            "类固醇", "兴奋剂", "禁药", "激素注射",
        }

        # 极端训练方法词汇（extreme_training）
        self.extreme_keywords = {
            "7天瘦", "快速减", "暴瘦", "极速",
            "不吃饭", "只喝水", "零碳水",
            "一周减10斤", "三天速成", "暴力增肌",
            "每天练6小时", "不休息连续训练", "疼痛就是成长",
        }

        # 政治敏感词汇
        self.political_keywords = set()

        # 违法违规词汇
        self.illegal_keywords = {
            "代购禁药", "地下药房", "黑市激素",
        }

        # 不当内容词汇
        self.inappropriate_keywords = {
            "色情", "裸体训练", "性暗示",
        }
    
    def _init_patterns(self):
        """初始化正则模式"""
        # 医疗建议模式
        self.medical_patterns = [
            r"你(应该|需要|必须)(去)?看医生",
            r"建议(你)?(去)?医院",
            r"这(可能|应该)是.{0,10}(病|症)",
            r"(吃|服用).{0,5}药",
        ]
        
        # 危险建议模式
        self.dangerous_patterns = [
            r"(每天|一天)(只)?(吃|摄入).{0,5}(卡|千卡|大卡)",
            r"(连续|持续).{0,5}(断食|绝食)",
            r"(忽视|无视|不管).{0,5}(疼痛|不适)",
        ]
        
        # 编译正则表达式
        self.compiled_medical_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.medical_patterns
        ]
        self.compiled_dangerous_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.dangerous_patterns
        ]
    
    def _init_disclaimers(self):
        """初始化免责声明"""
        self.disclaimers = {
            "default": "\n\n---\n本内容由智能系统辅助生成，仅供参考。",
            "training_plan": "\n\n---\n训练计划基于专业数据库生成，请根据个人情况调整。如有不适请立即停止训练。",
            "nutrition": "\n\n---\n营养建议仅供参考，如有特殊健康状况请咨询专业医生或营养师。",
            "medical_warning": "\n\n⚠️ 健身建议仅供参考，如有健康问题请咨询专业医生。",
            "safety_warning": "\n\n⚠️ 请在安全环境下进行训练，量力而行，如有不适请立即停止。",
        }
    
    def filter_input(self, content: str) -> FilterResult:
        """
        过滤用户输入
        
        Args:
            content: 用户输入内容
            
        Returns:
            FilterResult: 过滤结果
        """
        result = FilterResult(risk_level=ContentRiskLevel.SAFE)
        
        # 检测各类敏感内容
        self._check_self_harm_content(content, result)
        self._check_dangerous_substances(content, result)
        self._check_medical_content(content, result)
        self._check_dangerous_content(content, result)
        self._check_extreme_content(content, result)
        self._check_political_content(content, result)
        self._check_illegal_content(content, result)
        
        # 确定最终风险等级
        self._determine_risk_level(result)
        
        return result
    
    def filter_output(
        self, 
        content: str, 
        content_type: str = "default"
    ) -> Tuple[str, FilterResult]:
        """
        过滤系统输出
        
        Args:
            content: 系统生成的内容
            content_type: 内容类型（default/training_plan/nutrition）
            
        Returns:
            Tuple[str, FilterResult]: (处理后的内容, 过滤结果)
        """
        result = FilterResult(risk_level=ContentRiskLevel.SAFE)
        
        # 检测输出内容
        self._check_medical_content(content, result)
        self._check_dangerous_content(content, result)
        self._check_extreme_content(content, result)
        
        # 确定风险等级
        self._determine_risk_level(result)
        
        # 处理内容
        processed_content = self._process_output(content, result, content_type)
        result.modified_content = processed_content
        
        return processed_content, result
    
    def _check_medical_content(self, content: str, result: FilterResult):
        """检测医疗相关内容"""
        content_lower = content.lower()
        
        # 关键词检测
        for keyword in self.medical_keywords:
            if keyword in content_lower:
                result.matched_keywords.append(keyword)
                if ContentCategory.MEDICAL not in result.categories:
                    result.categories.append(ContentCategory.MEDICAL)
        
        # 模式检测
        for pattern in self.compiled_medical_patterns:
            if pattern.search(content):
                result.warnings.append("检测到医疗相关表述")
                if ContentCategory.MEDICAL not in result.categories:
                    result.categories.append(ContentCategory.MEDICAL)
    
    def _check_dangerous_content(self, content: str, result: FilterResult):
        """检测危险内容"""
        content_lower = content.lower()
        
        # 关键词检测
        for keyword in self.dangerous_keywords:
            if keyword in content_lower:
                result.matched_keywords.append(keyword)
                if ContentCategory.DANGEROUS not in result.categories:
                    result.categories.append(ContentCategory.DANGEROUS)
        
        # 模式检测
        for pattern in self.compiled_dangerous_patterns:
            if pattern.search(content):
                result.warnings.append("检测到危险建议")
                if ContentCategory.DANGEROUS not in result.categories:
                    result.categories.append(ContentCategory.DANGEROUS)
    
    def _check_extreme_content(self, content: str, result: FilterResult):
        """检测极端方法"""
        content_lower = content.lower()

        for keyword in self.extreme_keywords:
            if keyword in content_lower:
                result.matched_keywords.append(keyword)
                if ContentCategory.EXTREME not in result.categories:
                    result.categories.append(ContentCategory.EXTREME)

    def _check_self_harm_content(self, content: str, result: FilterResult):
        """检测自我伤害内容"""
        content_lower = content.lower()

        for keyword in self.self_harm_keywords:
            if keyword in content_lower:
                result.matched_keywords.append(keyword)
                if ContentCategory.SELF_HARM not in result.categories:
                    result.categories.append(ContentCategory.SELF_HARM)
                result.should_block = True
                result.warnings.append("检测到自我伤害相关内容")

    def _check_dangerous_substances(self, content: str, result: FilterResult):
        """检测危险物质内容"""
        content_lower = content.lower()

        for keyword in self.dangerous_substances_keywords:
            if keyword.lower() in content_lower:
                result.matched_keywords.append(keyword)
                if ContentCategory.DANGEROUS_SUBSTANCE not in result.categories:
                    result.categories.append(ContentCategory.DANGEROUS_SUBSTANCE)
                result.warnings.append("检测到危险物质相关内容")
    
    def _check_political_content(self, content: str, result: FilterResult):
        """检测政治敏感内容"""
        content_lower = content.lower()
        
        for keyword in self.political_keywords:
            if keyword in content_lower:
                result.matched_keywords.append(keyword)
                if ContentCategory.POLITICAL not in result.categories:
                    result.categories.append(ContentCategory.POLITICAL)
                result.should_block = True
    
    def _check_illegal_content(self, content: str, result: FilterResult):
        """检测违法违规内容"""
        content_lower = content.lower()
        
        for keyword in self.illegal_keywords:
            if keyword in content_lower:
                result.matched_keywords.append(keyword)
                if ContentCategory.ILLEGAL not in result.categories:
                    result.categories.append(ContentCategory.ILLEGAL)
                result.should_block = True
    
    def _determine_risk_level(self, result: FilterResult):
        """确定风险等级"""
        if result.should_block:
            result.risk_level = ContentRiskLevel.BLOCKED
            return

        # 根据类别确定风险等级（从高到低）
        if ContentCategory.ILLEGAL in result.categories:
            result.risk_level = ContentRiskLevel.BLOCKED
            result.should_block = True
        elif ContentCategory.POLITICAL in result.categories:
            result.risk_level = ContentRiskLevel.BLOCKED
            result.should_block = True
        elif ContentCategory.SELF_HARM in result.categories:
            result.risk_level = ContentRiskLevel.BLOCKED
            result.should_block = True
        elif ContentCategory.DANGEROUS in result.categories:
            result.risk_level = ContentRiskLevel.HIGH
            result.requires_review = True
        elif ContentCategory.DANGEROUS_SUBSTANCE in result.categories:
            result.risk_level = ContentRiskLevel.HIGH
            result.requires_review = True
        elif ContentCategory.EXTREME in result.categories:
            result.risk_level = ContentRiskLevel.MEDIUM
        elif ContentCategory.MEDICAL in result.categories:
            result.risk_level = ContentRiskLevel.LOW
        else:
            result.risk_level = ContentRiskLevel.SAFE
    
    def _process_output(
        self, 
        content: str, 
        result: FilterResult, 
        content_type: str
    ) -> str:
        """处理输出内容"""
        if result.should_block:
            return "抱歉，我无法回答这个问题。请尝试其他健身相关的问题。"
        
        processed = content
        
        # 根据风险等级添加警告
        if result.risk_level == ContentRiskLevel.HIGH:
            processed = self._add_safety_warning(processed)
        elif result.risk_level == ContentRiskLevel.MEDIUM:
            processed = self._add_caution_note(processed)
        
        # 添加医疗提示
        if ContentCategory.MEDICAL in result.categories:
            processed = self._add_medical_disclaimer(processed)
        
        # 添加内容标识
        processed = self._add_content_label(processed, content_type)
        
        return processed
    
    def _add_safety_warning(self, content: str) -> str:
        """添加安全警告"""
        warning = self.disclaimers["safety_warning"]
        return content + warning
    
    def _add_caution_note(self, content: str) -> str:
        """添加注意提示"""
        note = "\n\n💡 提示：请根据自身情况适当调整，循序渐进。"
        return content + note
    
    def _add_medical_disclaimer(self, content: str) -> str:
        """添加医疗免责声明"""
        disclaimer = self.disclaimers["medical_warning"]
        return content + disclaimer
    
    def _add_content_label(self, content: str, content_type: str) -> str:
        """添加内容标识"""
        # 检查是否已有标识
        if "本内容由智能系统辅助生成" in content:
            return content
        
        # 根据内容类型选择标识
        label = self.disclaimers.get(content_type, self.disclaimers["default"])
        return content + label
    
    def get_blocked_response(self) -> str:
        """获取被阻止时的响应"""
        return "抱歉，我无法回答这个问题。作为健身顾问，我只能提供健身训练和营养相关的建议。请尝试其他健身相关的问题。"
    
    def get_medical_redirect_response(self) -> str:
        """获取医疗重定向响应"""
        return "您的问题涉及医疗健康领域，建议您咨询专业医生获取准确的医疗建议。我可以为您提供健身训练和营养方面的指导。"


# 单例实例
_content_safety_filter: Optional[ContentSafetyFilter] = None


def get_content_safety_filter() -> ContentSafetyFilter:
    """获取内容安全过滤器单例"""
    global _content_safety_filter
    if _content_safety_filter is None:
        _content_safety_filter = ContentSafetyFilter()
    return _content_safety_filter
