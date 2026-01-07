# -*- coding: utf-8 -*-
"""
Training Plan Summarizer Service

训练计划摘要服务，实现精简输出和格式优化。
核心功能：
- 控制输出长度在8000字符以内
- 只保留核心字段
- 动作名转换为Markdown链接
- 高风险动作添加⚠️标记

Requirements: 11.1, 11.2, 11.3, 11.4 - 训练计划摘要优化

作者: BUILD_BODY Team
版本: 1.0.0
日期: 2025-12-26
"""

import logging
import json
import re
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class SummaryConfig:
    """摘要配置"""
    max_output_chars: int = 8000
    core_fields: List[str] = field(default_factory=lambda: [
        'exercise_id', 'name_zh', 'sets', 'reps_range', 'rest_seconds', 'weight_suggestion'
    ])
    exercise_link_template: str = "/exercise/{exercise_id}"
    high_risk_marker: str = "⚠️"
    include_safety_notes: bool = True
    include_cycle_explanation: bool = True


@dataclass
class SummaryResult:
    """摘要结果"""
    content: str
    char_count: int
    is_truncated: bool
    truncation_reason: Optional[str] = None
    exercise_count: int = 0
    high_risk_count: int = 0


class TrainingPlanSummarizer:
    """
    训练计划摘要服务
    
    核心功能：
    - summarize: 精简训练计划输出
    - convert_to_links: 将动作名转换为Markdown链接
    - add_safety_markers: 为高风险动作添加⚠️标记
    
    Requirements: 11.1, 11.2, 11.3, 11.4 - 训练计划摘要优化
    """
    
    # 高风险动作关键词（用于识别高风险动作）
    HIGH_RISK_KEYWORDS = {
        'deadlift', 'squat', 'snatch', 'clean', 'jerk',
        'overhead press', 'behind neck', 'good morning',
        '硬拉', '深蹲', '抓举', '挺举', '颈后推举', '早安式体前屈'
    }
    
    # 高风险动作ID列表（精确匹配）
    HIGH_RISK_EXERCISE_IDS = {
        'barbell_deadlift', 'sumo_deadlift', 'romanian_deadlift',
        'barbell_squat', 'front_squat', 'overhead_squat',
        'barbell_snatch', 'power_clean', 'clean_and_jerk',
        'behind_neck_press', 'good_morning'
    }
    
    # 核心字段（精简输出时保留的字段）
    CORE_FIELDS = [
        'exercise_id', 'name_zh', 'name_en', 'sets', 
        'reps_range', 'rest_seconds', 'weight_suggestion'
    ]
    
    # 可选字段（空间允许时保留）
    OPTIONAL_FIELDS = [
        'primary_muscles', 'safety_marker', 'safety_notes'
    ]
    
    def __init__(self, config: Optional[SummaryConfig] = None):
        """
        初始化训练计划摘要器
        
        Args:
            config: 摘要配置（可选）
        """
        self.config = config or SummaryConfig()
        logger.info(f"TrainingPlanSummarizer initialized: max_chars={self.config.max_output_chars}")
    
    def summarize(
        self,
        plan: Dict[str, Any],
        include_explanation: bool = True,
        include_safety: bool = True
    ) -> SummaryResult:
        """
        精简训练计划输出
        
        将完整的训练计划精简为核心内容，控制在8000字符以内。
        
        Args:
            plan: 完整训练计划
            include_explanation: 是否包含周期说明
            include_safety: 是否包含安全提醒
            
        Returns:
            SummaryResult: 摘要结果
            
        Requirements: 11.1 - 单次输出控制在8000字符以内
        """
        logger.info("开始生成训练计划摘要")
        
        # 第一步：提取核心字段
        summarized_plan = self._extract_core_fields(plan)
        
        # 第二步：转换动作链接
        summarized_plan = self.convert_to_links(summarized_plan)
        
        # 第三步：添加安全标记
        summarized_plan = self.add_safety_markers(summarized_plan)
        
        # 第四步：生成输出文本
        output_parts = []
        
        # 添加周期说明（如果有）
        if include_explanation and 'cycle_explanation' in plan:
            output_parts.append(plan['cycle_explanation'])
            output_parts.append("")  # 空行分隔
        
        # 添加训练日内容
        training_days_text = self._format_training_days(summarized_plan)
        output_parts.append(training_days_text)
        
        # 添加下周预览（如果有）
        if 'next_week_preview' in plan and plan['next_week_preview']:
            output_parts.append("")
            output_parts.append(plan['next_week_preview'])
        
        # 合并输出
        output = "\n".join(output_parts)
        
        # 检查长度并截断（如果需要）
        is_truncated = False
        truncation_reason = None
        
        if len(output) > self.config.max_output_chars:
            output, truncation_reason = self._truncate_output(output)
            is_truncated = True
            logger.warning(f"输出被截断: {truncation_reason}")
        
        # 统计信息
        exercise_count = self._count_exercises(summarized_plan)
        high_risk_count = self._count_high_risk_exercises(summarized_plan)
        
        result = SummaryResult(
            content=output,
            char_count=len(output),
            is_truncated=is_truncated,
            truncation_reason=truncation_reason,
            exercise_count=exercise_count,
            high_risk_count=high_risk_count
        )
        
        logger.info(
            f"摘要生成完成: chars={result.char_count}, "
            f"exercises={exercise_count}, high_risk={high_risk_count}, "
            f"truncated={is_truncated}"
        )
        
        return result

    
    def convert_to_links(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        将动作名转换为Markdown链接
        
        Args:
            plan: 训练计划
            
        Returns:
            Dict: 转换后的训练计划
            
        Requirements: 11.3 - 使用Markdown链接格式
        """
        converted_plan = plan.copy()
        
        if 'training_days' in converted_plan:
            for day in converted_plan['training_days']:
                if 'exercises' in day:
                    for exercise in day['exercises']:
                        exercise_id = exercise.get('exercise_id', '')
                        name_zh = exercise.get('name_zh', '')
                        
                        if exercise_id and name_zh:
                            # 生成Markdown链接
                            link = self.config.exercise_link_template.format(
                                exercise_id=exercise_id
                            )
                            exercise['name_link'] = f"[{name_zh}]({link})"
        
        return converted_plan
    
    def add_safety_markers(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        为高风险动作添加⚠️标记
        
        Args:
            plan: 训练计划
            
        Returns:
            Dict: 添加标记后的训练计划
            
        Requirements: 11.4 - 高风险动作添加⚠️标记
        """
        marked_plan = plan.copy()
        
        if 'training_days' in marked_plan:
            for day in marked_plan['training_days']:
                if 'exercises' in day:
                    for exercise in day['exercises']:
                        is_high_risk = self._is_high_risk_exercise(exercise)
                        
                        if is_high_risk:
                            exercise['safety_marker'] = self.config.high_risk_marker
                            
                            # 如果已有name_link，在前面添加标记
                            if 'name_link' in exercise:
                                exercise['name_link'] = (
                                    f"{self.config.high_risk_marker} {exercise['name_link']}"
                                )
        
        return marked_plan
    
    def _extract_core_fields(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取核心字段，移除非必要信息
        
        Requirements: 11.2 - 只保留核心字段
        """
        extracted = {}
        
        # 保留元数据
        for key in ['week_number', 'total_weeks', 'phase', 'phase_description',
                    'volume_multiplier', 'is_deload_week', 'rest_days',
                    'total_weekly_sets', 'generated_at']:
            if key in plan:
                extracted[key] = plan[key]
        
        # 处理训练日
        if 'training_days' in plan:
            extracted['training_days'] = []
            
            for day in plan['training_days']:
                extracted_day = {
                    'day_number': day.get('day_number'),
                    'day_name': day.get('day_name'),
                    'focus_muscle_groups': day.get('focus_muscle_groups', []),
                    'total_sets': day.get('total_sets', 0),
                    'estimated_duration_minutes': day.get('estimated_duration_minutes', 0),
                    'exercises': []
                }
                
                # 保留notes（如果是deload日）
                if day.get('is_deload_day') or day.get('notes'):
                    extracted_day['notes'] = day.get('notes', [])
                
                # 提取动作核心字段
                for exercise in day.get('exercises', []):
                    extracted_exercise = {}
                    
                    # 核心字段
                    for field in self.CORE_FIELDS:
                        if field in exercise:
                            extracted_exercise[field] = exercise[field]
                    
                    # 安全相关字段（始终保留）
                    if exercise.get('safety_marker'):
                        extracted_exercise['safety_marker'] = exercise['safety_marker']
                    if exercise.get('safety_notes'):
                        extracted_exercise['safety_notes'] = exercise['safety_notes']
                    
                    extracted_day['exercises'].append(extracted_exercise)
                
                extracted['training_days'].append(extracted_day)
        
        return extracted
    
    def _format_training_days(self, plan: Dict[str, Any]) -> str:
        """格式化训练日为文本输出"""
        lines = []
        
        # 添加周信息头
        week_num = plan.get('week_number', 1)
        total_weeks = plan.get('total_weeks', 4)
        phase = plan.get('phase', '')
        
        lines.append(f"## 第{week_num}训练周期训练计划 ({phase})")
        lines.append("")
        
        # 格式化每个训练日
        for day in plan.get('training_days', []):
            day_num = day.get('day_number', 1)
            day_name = day.get('day_name', f'训练日{day_num}')
            focus = ', '.join(day.get('focus_muscle_groups', []))
            duration = day.get('estimated_duration_minutes', 60)
            
            lines.append(f"### Day {day_num}: {day_name}")
            if focus:
                lines.append(f"**目标肌群**: {focus}")
            lines.append(f"**预计时长**: {duration}分钟")
            lines.append("")
            
            # 添加notes（如果有）
            notes = day.get('notes', [])
            if notes:
                for note in notes:
                    lines.append(f"> {note}")
                lines.append("")
            
            # 格式化动作列表
            lines.append("| 动作 | 组数 | 次数 | 休息 | 重量建议 |")
            lines.append("|------|------|------|------|----------|")
            
            for exercise in day.get('exercises', []):
                name = exercise.get('name_link', exercise.get('name_zh', '未知动作'))
                sets = exercise.get('sets', 3)
                reps = exercise.get('reps_range', (8, 12))
                if isinstance(reps, (list, tuple)) and len(reps) == 2:
                    reps_str = f"{reps[0]}-{reps[1]}"
                else:
                    reps_str = str(reps)
                rest = exercise.get('rest_seconds', 90)
                weight = exercise.get('weight_suggestion', '-')
                
                lines.append(f"| {name} | {sets} | {reps_str} | {rest}s | {weight or '-'} |")
            
            lines.append("")
        
        # 添加休息日信息
        rest_days = plan.get('rest_days', [])
        if rest_days:
            rest_days_str = ', '.join([f"Day {d}" for d in rest_days])
            lines.append(f"**休息日**: {rest_days_str}")
        
        # 添加总训练量
        total_sets = plan.get('total_weekly_sets', 0)
        lines.append(f"**本周总组数**: {total_sets}组")
        
        return "\n".join(lines)
    
    def _truncate_output(self, output: str) -> tuple:
        """
        截断输出以符合长度限制
        
        Returns:
            tuple: (截断后的输出, 截断原因)
        """
        max_chars = self.config.max_output_chars
        
        if len(output) <= max_chars:
            return output, None
        
        # 策略1: 尝试移除可选内容
        lines = output.split('\n')
        essential_lines = []
        optional_lines = []
        
        for line in lines:
            # 识别可选内容（如详细说明、额外备注）
            if line.startswith('>') or line.startswith('💡') or line.startswith('📊'):
                optional_lines.append(line)
            else:
                essential_lines.append(line)
        
        truncated = '\n'.join(essential_lines)
        
        if len(truncated) <= max_chars:
            return truncated, "移除了可选说明内容"
        
        # 策略2: 硬截断
        truncated = output[:max_chars - 50]
        # 找到最后一个完整行
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.8:
            truncated = truncated[:last_newline]
        
        truncated += "\n\n... (内容已截断，请查看完整计划)"
        
        return truncated, f"输出超过{max_chars}字符限制，已硬截断"
    
    def _is_high_risk_exercise(self, exercise: Dict[str, Any]) -> bool:
        """判断是否为高风险动作"""
        # 检查已有的安全标记
        if exercise.get('safety_marker'):
            return True
        
        # 检查exercise_id
        exercise_id = exercise.get('exercise_id', '').lower()
        if exercise_id in self.HIGH_RISK_EXERCISE_IDS:
            return True
        
        # 检查动作名称关键词
        name_zh = exercise.get('name_zh', '').lower()
        name_en = exercise.get('name_en', '').lower()
        
        for keyword in self.HIGH_RISK_KEYWORDS:
            if keyword in name_zh or keyword in name_en:
                return True
        
        return False
    
    def _count_exercises(self, plan: Dict[str, Any]) -> int:
        """统计动作数量"""
        count = 0
        for day in plan.get('training_days', []):
            count += len(day.get('exercises', []))
        return count
    
    def _count_high_risk_exercises(self, plan: Dict[str, Any]) -> int:
        """统计高风险动作数量"""
        count = 0
        for day in plan.get('training_days', []):
            for exercise in day.get('exercises', []):
                if exercise.get('safety_marker'):
                    count += 1
        return count
    
    def summarize_to_dict(
        self,
        plan: Dict[str, Any],
        include_explanation: bool = True
    ) -> Dict[str, Any]:
        """
        精简训练计划并返回字典格式
        
        与summarize不同，此方法返回结构化数据而非文本。
        
        Args:
            plan: 完整训练计划
            include_explanation: 是否包含周期说明
            
        Returns:
            Dict: 精简后的训练计划字典
        """
        # 提取核心字段
        summarized = self._extract_core_fields(plan)
        
        # 转换链接
        summarized = self.convert_to_links(summarized)
        
        # 添加安全标记
        summarized = self.add_safety_markers(summarized)
        
        # 添加周期说明
        if include_explanation and 'cycle_explanation' in plan:
            summarized['cycle_explanation'] = plan['cycle_explanation']
        
        # 添加下周预览
        if 'next_week_preview' in plan:
            summarized['next_week_preview'] = plan['next_week_preview']
        
        return summarized
    
    def estimate_output_length(self, plan: Dict[str, Any]) -> int:
        """
        估算输出长度
        
        用于在生成前预估是否会超过限制。
        
        Args:
            plan: 训练计划
            
        Returns:
            int: 估算的字符数
        """
        # 基础长度（元数据、标题等）
        base_length = 500
        
        # 周期说明长度
        if 'cycle_explanation' in plan:
            base_length += len(plan['cycle_explanation'])
        
        # 每个训练日的估算长度
        for day in plan.get('training_days', []):
            # 日标题和元数据
            base_length += 150
            
            # 每个动作约100字符
            exercise_count = len(day.get('exercises', []))
            base_length += exercise_count * 100
        
        return base_length
