# -*- coding: utf-8 -*-
"""
Safety Reminder Generator Service

安全提醒生成服务，实现免责声明、损伤历史提醒和高风险动作标记。
核心功能：
- 生成免责声明
- 根据用户损伤历史生成针对性提醒
- 标记高风险动作
- 获取动作禁忌条件

Requirements: 14.1, 14.2, 14.3, 14.4 - 安全提醒系统

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import logging
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class SafetyConfig:
    """安全配置"""
    high_risk_marker: str = "⚠️"
    warning_marker: str = "⚠️"
    include_disclaimer: bool = True
    include_injury_reminder: bool = True
    disclaimer_version: str = "1.0"


@dataclass
class SafetyReminder:
    """安全提醒结果"""
    disclaimer: str
    injury_reminders: List[str]
    high_risk_exercises: List[str]
    contraindications: Dict[str, List[str]]
    generated_at: str


class SafetyReminderGenerator:
    """
    安全提醒生成服务
    
    核心功能：
    - generate_disclaimer: 生成免责声明
    - generate_injury_reminder: 根据损伤历史生成提醒
    - mark_high_risk_exercises: 标记高风险动作
    - get_contraindications: 获取动作禁忌条件
    
    Requirements: 14.1, 14.2, 14.3, 14.4 - 安全提醒系统
    """
    
    # 高风险动作ID列表（精确匹配）
    HIGH_RISK_EXERCISE_IDS: Set[str] = {
        # 硬拉变体
        'barbell_deadlift', 'sumo_deadlift', 'romanian_deadlift',
        'stiff_leg_deadlift', 'deficit_deadlift',
        # 深蹲变体
        'barbell_squat', 'front_squat', 'overhead_squat',
        'hack_squat', 'zercher_squat',
        # 奥林匹克举重
        'barbell_snatch', 'power_snatch', 'hang_snatch',
        'power_clean', 'hang_clean', 'clean_and_jerk',
        # 高风险推举
        'behind_neck_press', 'behind_neck_pulldown',
        # 其他高风险动作
        'good_morning', 'barbell_row_underhand'
    }
    
    # 高风险动作关键词（用于名称匹配）
    HIGH_RISK_KEYWORDS: Set[str] = {
        'deadlift', 'squat', 'snatch', 'clean', 'jerk',
        'overhead press', 'behind neck', 'good morning',
        '硬拉', '深蹲', '抓举', '挺举', '颈后推举', '颈后下拉',
        '早安式体前屈', '杠铃划船'
    }
    
    # 身体部位到中文名称的映射
    BODY_PART_NAMES: Dict[str, str] = {
        'shoulder': '肩部',
        'knee': '膝盖',
        'lower_back': '下背部',
        'wrist': '手腕',
        'elbow': '肘部',
        'neck': '颈部',
        'hip': '髋部',
        'ankle': '脚踝',
        'rotator_cuff': '肩袖',
        'spine': '脊柱'
    }
    
    # 损伤部位对应的禁忌动作
    INJURY_CONTRAINDICATIONS: Dict[str, List[str]] = {
        'shoulder': [
            'behind_neck_press', 'behind_neck_pulldown', 
            'upright_row', 'overhead_squat'
        ],
        'rotator_cuff': [
            'behind_neck_press', 'behind_neck_pulldown',
            'upright_row', 'dips', 'overhead_press'
        ],
        'lower_back': [
            'barbell_deadlift', 'good_morning', 'barbell_row',
            'romanian_deadlift', 'stiff_leg_deadlift'
        ],
        'knee': [
            'barbell_squat', 'front_squat', 'leg_extension',
            'lunges', 'jump_squat'
        ],
        'wrist': [
            'front_squat', 'clean', 'snatch',
            'barbell_curl', 'wrist_curl'
        ],
        'neck': [
            'behind_neck_press', 'behind_neck_pulldown',
            'shrugs', 'neck_extension'
        ],
        'hip': [
            'barbell_squat', 'sumo_deadlift', 'hip_thrust',
            'lunges', 'bulgarian_split_squat'
        ],
        'elbow': [
            'skull_crusher', 'tricep_dips', 'close_grip_bench',
            'preacher_curl'
        ]
    }
    
    # 动作禁忌条件
    EXERCISE_CONTRAINDICATIONS: Dict[str, List[str]] = {
        'barbell_deadlift': [
            '下背部损伤或疼痛',
            '椎间盘突出',
            '严重的髋关节问题',
            '孕妇（中后期）'
        ],
        'barbell_squat': [
            '膝盖损伤或疼痛',
            '下背部问题',
            '髋关节活动度受限',
            '平衡能力严重不足'
        ],
        'behind_neck_press': [
            '肩袖损伤',
            '肩关节不稳定',
            '颈椎问题',
            '肩关节活动度受限'
        ],
        'good_morning': [
            '下背部损伤',
            '椎间盘问题',
            '腘绳肌拉伤',
            '核心力量不足'
        ],
        'power_clean': [
            '手腕损伤',
            '肩关节问题',
            '下背部损伤',
            '技术不熟练（需要专业指导）'
        ],
        'overhead_squat': [
            '肩关节活动度不足',
            '踝关节活动度不足',
            '核心稳定性不足',
            '任何上肢损伤'
        ]
    }
    
    # 免责声明模板
    DISCLAIMER_TEMPLATE: str = """⚠️ **重要安全提醒**

本训练计划由AI系统生成，仅供参考。在开始任何新的训练计划之前，请注意：

1. **咨询专业人士**：建议在开始训练前咨询医生或专业健身教练，特别是如果您有任何健康问题或损伤历史。

2. **量力而行**：根据自身情况调整训练强度和重量，不要勉强完成超出能力范围的动作。

3. **正确姿势**：确保掌握正确的动作技术，必要时寻求专业指导。错误的姿势可能导致受伤。

4. **热身与拉伸**：每次训练前进行充分热身，训练后进行适当拉伸。

5. **倾听身体**：如果感到疼痛或不适，请立即停止训练并寻求医疗建议。

6. **循序渐进**：不要急于增加重量或强度，遵循渐进过载原则。

**免责声明**：本系统提供的训练建议不构成医疗建议。使用者需自行承担训练风险。如有任何健康问题，请咨询专业医疗人员。

---
"""
    
    # 损伤提醒模板
    INJURY_REMINDER_TEMPLATE: str = """🏥 **个人健康提醒**

根据您的档案记录，您有以下损伤历史：
{injury_list}

**针对性建议**：
{recommendations}

请在训练中特别注意以上部位，如有不适请立即停止。

---
"""
    
    def __init__(self, config: Optional[SafetyConfig] = None):
        """
        初始化安全提醒生成器
        
        Args:
            config: 安全配置（可选）
        """
        self.config = config or SafetyConfig()
        logger.info(f"SafetyReminderGenerator initialized: version={self.config.disclaimer_version}")
    
    def generate_disclaimer(self) -> str:
        """
        生成免责声明
        
        Returns:
            str: 免责声明文本
            
        Requirements: 14.1 - 在计划开头添加免责声明
        """
        logger.debug("生成免责声明")
        return self.DISCLAIMER_TEMPLATE
    
    def generate_injury_reminder(self, user_profile: Dict[str, Any]) -> str:
        """
        根据用户损伤历史生成针对性提醒
        
        Args:
            user_profile: 用户档案，包含损伤历史
            
        Returns:
            str: 损伤提醒文本，如果没有损伤历史则返回空字符串
            
        Requirements: 14.3 - 用户有损伤历史时添加针对性提醒
        """
        # 获取损伤历史
        injury_history = user_profile.get('injury_history', [])
        
        if not injury_history:
            logger.debug("用户无损伤历史，跳过损伤提醒")
            return ""
        
        logger.info(f"生成损伤提醒: {len(injury_history)}个损伤记录")
        
        # 构建损伤列表
        injury_items = []
        recommendations = []
        
        for injury in injury_history:
            # 支持字符串或字典格式
            if isinstance(injury, str):
                body_part = injury
                injury_date = None
                injury_status = 'unknown'
            else:
                body_part = injury.get('body_part', injury.get('part', ''))
                injury_date = injury.get('date', injury.get('injury_date'))
                injury_status = injury.get('status', 'unknown')
            
            # 获取中文名称
            body_part_zh = self.BODY_PART_NAMES.get(body_part, body_part)
            
            # 构建损伤描述
            if injury_date:
                injury_items.append(f"- {body_part_zh}（{injury_date}）")
            else:
                injury_items.append(f"- {body_part_zh}")
            
            # 生成针对性建议
            recommendation = self._get_injury_recommendation(body_part)
            if recommendation:
                recommendations.append(recommendation)
        
        # 如果没有有效的损伤记录
        if not injury_items:
            return ""
        
        # 格式化输出
        injury_list = "\n".join(injury_items)
        recommendations_text = "\n".join(recommendations) if recommendations else "- 请根据自身情况调整训练强度"
        
        return self.INJURY_REMINDER_TEMPLATE.format(
            injury_list=injury_list,
            recommendations=recommendations_text
        )
    
    def _get_injury_recommendation(self, body_part: str) -> str:
        """获取针对特定损伤部位的建议"""
        recommendations = {
            'shoulder': "- 肩部：避免颈后推举和高位下拉，使用较轻重量进行肩部训练",
            'rotator_cuff': "- 肩袖：避免过头推举动作，加强肩袖稳定性训练",
            'lower_back': "- 下背部：避免硬拉和早安式体前屈，加强核心稳定性",
            'knee': "- 膝盖：避免深蹲和腿屈伸，可选择腿举等低冲击动作",
            'wrist': "- 手腕：避免前蹲和奥林匹克举重，使用护腕保护",
            'neck': "- 颈部：避免颈后动作和耸肩，注意头部位置",
            'hip': "- 髋部：避免深蹲和弓步，可选择髋关节友好的替代动作",
            'elbow': "- 肘部：避免颅骨粉碎者和窄握卧推，使用较轻重量"
        }
        return recommendations.get(body_part, "")
    
    def mark_high_risk_exercises(self, exercises: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        标记高风险动作
        
        Args:
            exercises: 动作列表
            
        Returns:
            List[Dict]: 添加安全标记后的动作列表
            
        Requirements: 14.2 - 高风险动作添加⚠️标记和安全提示
        """
        logger.debug(f"检查{len(exercises)}个动作的风险等级")
        
        marked_exercises = []
        high_risk_count = 0
        
        for exercise in exercises:
            marked_exercise = exercise.copy()
            
            if self._is_high_risk_exercise(exercise):
                marked_exercise['safety_marker'] = self.config.high_risk_marker
                marked_exercise['is_high_risk'] = True
                
                # 添加安全提示
                exercise_id = exercise.get('exercise_id', '')
                safety_notes = self._get_safety_notes(exercise_id)
                if safety_notes:
                    marked_exercise['safety_notes'] = safety_notes
                
                high_risk_count += 1
            else:
                marked_exercise['is_high_risk'] = False
            
            marked_exercises.append(marked_exercise)
        
        logger.info(f"标记完成: {high_risk_count}/{len(exercises)}个高风险动作")
        return marked_exercises
    
    def _is_high_risk_exercise(self, exercise: Dict[str, Any]) -> bool:
        """判断是否为高风险动作"""
        # 检查已有的安全标记
        if exercise.get('safety_marker') or exercise.get('is_high_risk'):
            return True
        
        # 检查exercise_id
        exercise_id = exercise.get('exercise_id', '').lower()
        if exercise_id in self.HIGH_RISK_EXERCISE_IDS:
            return True
        
        # 检查动作名称关键词
        name_zh = exercise.get('name_zh', '').lower()
        name_en = exercise.get('name_en', '').lower()
        
        for keyword in self.HIGH_RISK_KEYWORDS:
            keyword_lower = keyword.lower()
            if keyword_lower in name_zh or keyword_lower in name_en or keyword_lower in exercise_id:
                return True
        
        return False
    
    def _get_safety_notes(self, exercise_id: str) -> str:
        """获取动作的安全提示"""
        safety_notes = {
            'barbell_deadlift': "保持背部挺直，核心收紧，避免弓背",
            'barbell_squat': "膝盖与脚尖方向一致，下蹲时保持核心稳定",
            'behind_neck_press': "肩关节活动度不足者慎用，建议使用前推替代",
            'good_morning': "保持背部挺直，动作幅度根据柔韧性调整",
            'power_clean': "需要专业指导，确保技术正确后再增加重量",
            'overhead_squat': "需要良好的肩部和踝部活动度，建议从空杆开始",
            'sumo_deadlift': "髋关节活动度要求高，注意膝盖外展方向",
            'front_squat': "手腕灵活性要求高，可使用交叉握法替代"
        }
        return safety_notes.get(exercise_id, "")
    
    def get_contraindications(self, exercise_id: str) -> List[str]:
        """
        获取动作禁忌条件
        
        Args:
            exercise_id: 动作ID
            
        Returns:
            List[str]: 禁忌条件列表
            
        Requirements: 14.4 - 显示禁忌条件列表
        """
        contraindications = self.EXERCISE_CONTRAINDICATIONS.get(exercise_id, [])
        
        if not contraindications:
            # 检查是否为高风险动作，提供通用禁忌
            if exercise_id in self.HIGH_RISK_EXERCISE_IDS:
                contraindications = [
                    "相关部位有损伤或疼痛",
                    "技术不熟练（建议寻求专业指导）",
                    "核心力量不足"
                ]
        
        logger.debug(f"获取禁忌条件: {exercise_id} -> {len(contraindications)}条")
        return contraindications
    
    def get_exercises_to_avoid(self, injury_history: List[Any]) -> List[str]:
        """
        根据损伤历史获取应避免的动作列表
        
        Args:
            injury_history: 损伤历史列表
            
        Returns:
            List[str]: 应避免的动作ID列表
        """
        exercises_to_avoid = set()
        
        for injury in injury_history:
            # 支持字符串或字典格式
            if isinstance(injury, str):
                body_part = injury
            else:
                body_part = injury.get('body_part', injury.get('part', ''))
            
            # 获取该部位的禁忌动作
            contraindicated = self.INJURY_CONTRAINDICATIONS.get(body_part, [])
            exercises_to_avoid.update(contraindicated)
        
        return list(exercises_to_avoid)
    
    def generate_full_safety_section(
        self,
        user_profile: Optional[Dict[str, Any]] = None,
        exercises: Optional[List[Dict[str, Any]]] = None
    ) -> SafetyReminder:
        """
        生成完整的安全提醒部分
        
        Args:
            user_profile: 用户档案（可选）
            exercises: 动作列表（可选）
            
        Returns:
            SafetyReminder: 完整的安全提醒结果
        """
        logger.info("生成完整安全提醒部分")
        
        # 生成免责声明
        disclaimer = self.generate_disclaimer() if self.config.include_disclaimer else ""
        
        # 生成损伤提醒
        injury_reminders = []
        if user_profile and self.config.include_injury_reminder:
            injury_reminder = self.generate_injury_reminder(user_profile)
            if injury_reminder:
                injury_reminders.append(injury_reminder)
        
        # 标记高风险动作
        high_risk_exercises = []
        contraindications = {}
        
        if exercises:
            marked = self.mark_high_risk_exercises(exercises)
            for ex in marked:
                if ex.get('is_high_risk'):
                    exercise_id = ex.get('exercise_id', '')
                    high_risk_exercises.append(exercise_id)
                    
                    # 获取禁忌条件
                    contras = self.get_contraindications(exercise_id)
                    if contras:
                        contraindications[exercise_id] = contras
        
        return SafetyReminder(
            disclaimer=disclaimer,
            injury_reminders=injury_reminders,
            high_risk_exercises=high_risk_exercises,
            contraindications=contraindications,
            generated_at=datetime.now().isoformat()
        )
    
    def format_safety_section(self, safety_reminder: SafetyReminder) -> str:
        """
        格式化安全提醒为文本输出
        
        Args:
            safety_reminder: 安全提醒结果
            
        Returns:
            str: 格式化的安全提醒文本
        """
        parts = []
        
        # 添加免责声明
        if safety_reminder.disclaimer:
            parts.append(safety_reminder.disclaimer)
        
        # 添加损伤提醒
        for reminder in safety_reminder.injury_reminders:
            parts.append(reminder)
        
        # 添加高风险动作提醒
        if safety_reminder.high_risk_exercises:
            parts.append("⚠️ **本计划包含以下高风险动作**：")
            for exercise_id in safety_reminder.high_risk_exercises:
                contras = safety_reminder.contraindications.get(exercise_id, [])
                parts.append(f"- {exercise_id}")
                if contras:
                    for contra in contras[:3]:  # 最多显示3条
                        parts.append(f"  - 禁忌：{contra}")
            parts.append("")
        
        return "\n".join(parts)
