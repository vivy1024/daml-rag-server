# -*- coding: utf-8 -*-
"""
SkillManager - 技能管理器

核心职责：
1. 管理所有技能的三层数据
2. 提供load_skill工具供LLM按需加载
3. 生成system prompt中的技能列表
4. 支持技能匹配和推荐

渐进式披露工作流程：
1. LLM看到技能列表（~650 tokens）- get_system_prompt_skills()
2. LLM调用load_skill获取技能详情（~500 tokens/skill）- load_skill()
3. LLM根据技能指令调用工具
4. 安全检查 + 工具执行

Requirements: 8.1, 8.2

版本: v1.0.0
日期: 2026-01-11
作者: 薛小川
"""

import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from .skill_definition import (
    Skill,
    SkillMetadata,
    SkillContent,
    SkillExecution,
    SkillCategory,
)

if TYPE_CHECKING:
    from src.framework.adapters.domain_adapter import DAGTemplateDefinition, Layer3Rule

logger = logging.getLogger(__name__)


class SkillManager:
    """
    技能管理器
    
    核心职责：
    1. 管理所有技能的三层数据
    2. 提供load_skill工具供LLM按需加载
    3. 生成system prompt中的技能列表
    4. 支持技能匹配和推荐
    
    使用示例:
    ```python
    from src.framework.skills import SkillManager
    
    # 创建管理器
    manager = SkillManager()
    
    # 从DAG模板批量注册
    manager.register_from_dag_templates(dag_templates)
    
    # 生成system prompt技能列表
    skills_prompt = manager.get_system_prompt_skills()
    
    # 按需加载技能内容
    skill_md = manager.load_skill("complete_training_plan")
    
    # 匹配技能
    matched_skill = manager.match_skill_by_query("帮我制定训练计划")
    ```
    
    Requirements: 8.1, 8.2
    """
    
    def __init__(self):
        """初始化技能管理器"""
        self.skills: Dict[str, Skill] = {}
        self._loaded_skills: Dict[str, SkillContent] = {}  # 已加载的技能内容缓存
        self._load_count: Dict[str, int] = {}  # 技能加载次数统计
        
        logger.info("✅ SkillManager初始化完成")
    
    # =========================================================================
    # 技能注册方法
    # =========================================================================
    
    def register_skill(self, skill: Skill) -> None:
        """
        注册技能
        
        Args:
            skill: 技能实例
        """
        skill_id = skill.get_skill_id()
        self.skills[skill_id] = skill
        self._load_count[skill_id] = 0
        logger.info(f"📋 注册技能: {skill_id} ({skill.get_name()})")
    
    def register_from_dag_templates(
        self,
        templates: Dict[str, 'DAGTemplateDefinition']
    ) -> int:
        """
        从DAG模板批量注册技能
        
        这是Skills架构的核心方法，将现有的DAG模板转换为Skills格式。
        
        Args:
            templates: DAG模板字典（template_id -> DAGTemplateDefinition）
        
        Returns:
            int: 成功注册的技能数量
        
        Requirements: 8.1
        """
        count = 0
        for template_id, template in templates.items():
            try:
                skill = Skill.from_dag_template(template)
                self.register_skill(skill)
                count += 1
            except Exception as e:
                logger.error(f"❌ 从模板 {template_id} 创建技能失败: {e}")
        
        logger.info(f"✅ 从DAG模板注册了 {count}/{len(templates)} 个技能")
        return count
    
    def unregister_skill(self, skill_id: str) -> bool:
        """
        注销技能
        
        Args:
            skill_id: 技能ID
        
        Returns:
            bool: 是否成功注销
        """
        if skill_id in self.skills:
            del self.skills[skill_id]
            self._loaded_skills.pop(skill_id, None)
            self._load_count.pop(skill_id, None)
            logger.info(f"📋 注销技能: {skill_id}")
            return True
        return False
    
    # =========================================================================
    # System Prompt生成（Level 1）
    # =========================================================================
    
    def get_system_prompt_skills(self) -> str:
        """
        生成system prompt中的技能列表（Level 1）
        
        格式：
        ## 可用技能
        使用 load_skill(skill_id) 获取技能详情
        
        - greeting: 友好回应用户的问候和简单闲聊
        - complete_training_plan: 制定完整训练计划
        - nutrition_planning: 制定营养方案
        ...
        
        Returns:
            str: system prompt格式的技能列表
        
        Requirements: 8.1
        """
        if not self.skills:
            return "## 可用技能\n暂无可用技能"
        
        lines = [
            "## 可用技能",
            "使用 load_skill(skill_id) 获取技能详情后再执行",
            ""
        ]
        
        # 按类别分组
        categories: Dict[SkillCategory, List[Skill]] = {}
        for skill in self.skills.values():
            category = skill.get_category()
            if category not in categories:
                categories[category] = []
            categories[category].append(skill)
        
        # 按类别输出
        category_names = {
            SkillCategory.QUICK: "快速咨询",
            SkillCategory.TRAINING: "训练相关",
            SkillCategory.NUTRITION: "营养相关",
            SkillCategory.SAFETY: "安全评估",
            SkillCategory.COMPREHENSIVE: "综合方案",
            SkillCategory.CUSTOM: "其他",
        }
        
        # 按固定顺序输出类别
        category_order = [
            SkillCategory.QUICK,
            SkillCategory.TRAINING,
            SkillCategory.NUTRITION,
            SkillCategory.SAFETY,
            SkillCategory.COMPREHENSIVE,
            SkillCategory.CUSTOM,
        ]
        
        for category in category_order:
            if category in categories:
                skills = categories[category]
                lines.append(f"### {category_names.get(category, category.value)}")
                for skill in skills:
                    lines.append(skill.metadata.to_system_prompt_format())
                lines.append("")
        
        return "\n".join(lines)
    
    def get_system_prompt_skills_compact(self) -> str:
        """
        生成紧凑格式的技能列表（更少token）
        
        Returns:
            str: 紧凑格式的技能列表
        """
        if not self.skills:
            return "可用技能: 无"
        
        lines = ["可用技能 (使用load_skill加载详情):"]
        for skill in self.skills.values():
            lines.append(f"- {skill.metadata.skill_id}: {skill.metadata.description}")
        
        return "\n".join(lines)
    
    def estimate_system_prompt_tokens(self) -> int:
        """
        估算system prompt中技能列表的token数
        
        Returns:
            int: 预估token数
        """
        # 每个技能约50 tokens
        base_tokens = 50  # 标题和说明
        skill_tokens = len(self.skills) * 50
        return base_tokens + skill_tokens
    
    # =========================================================================
    # 技能加载（Level 2）
    # =========================================================================
    
    def load_skill(self, skill_id: str) -> str:
        """
        加载技能完整内容（Level 2）
        
        这是一个MCP工具，供LLM调用。
        返回SKILL.md格式的完整指令。
        
        Args:
            skill_id: 技能ID
        
        Returns:
            str: SKILL.md格式的技能内容，或错误信息
        
        Requirements: 8.2
        """
        skill = self.skills.get(skill_id)
        if not skill:
            available = ", ".join(self.skills.keys())
            return f"错误：技能 '{skill_id}' 不存在。可用技能: {available}"
        
        # 缓存已加载的技能
        self._loaded_skills[skill_id] = skill.content
        
        # 更新加载计数
        self._load_count[skill_id] = self._load_count.get(skill_id, 0) + 1
        
        logger.info(f"📖 加载技能: {skill_id} (第{self._load_count[skill_id]}次)")
        
        return skill.content.to_skill_md()
    
    def get_loaded_skill(self, skill_id: str) -> Optional[SkillContent]:
        """
        获取已加载的技能内容
        
        Args:
            skill_id: 技能ID
        
        Returns:
            SkillContent或None
        """
        return self._loaded_skills.get(skill_id)
    
    def get_loaded_skills(self) -> List[str]:
        """
        获取所有已加载的技能ID列表
        
        Returns:
            List[str]: 已加载的技能ID列表
        """
        return list(self._loaded_skills.keys())
    
    def clear_loaded_skills(self) -> None:
        """清除已加载的技能缓存"""
        self._loaded_skills.clear()
        logger.info("🧹 清除已加载技能缓存")
    
    # =========================================================================
    # 技能匹配
    # =========================================================================
    
    def match_skill_by_query(self, query: str) -> Optional[str]:
        """
        根据查询匹配最佳技能
        
        匹配逻辑：
        1. 关键词精确匹配（权重2）
        2. 关键词模糊匹配（权重1）
        3. 返回匹配度最高的技能ID
        
        Args:
            query: 用户查询
        
        Returns:
            str或None: 匹配的技能ID
        """
        if not query or not self.skills:
            return None
        
        query_lower = query.lower()
        
        best_match = None
        best_score = 0
        
        for skill in self.skills.values():
            score = 0
            
            # 关键词匹配
            for keyword in skill.metadata.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in query_lower:
                    score += 2  # 精确匹配
                elif any(k in keyword_lower for k in query_lower.split()):
                    score += 1  # 模糊匹配
            
            # 技能名称匹配
            if skill.metadata.name.lower() in query_lower:
                score += 3
            
            # 描述匹配
            if any(word in skill.metadata.description.lower() for word in query_lower.split() if len(word) > 1):
                score += 0.5
            
            if score > best_score:
                best_score = score
                best_match = skill.metadata.skill_id
        
        if best_match and best_score > 0:
            logger.debug(f"🎯 技能匹配: '{query[:30]}...' -> {best_match} (score={best_score})")
        
        return best_match if best_score > 0 else None
    
    def match_skills_by_query(
        self,
        query: str,
        top_k: int = 3
    ) -> List[Dict[str, Any]]:
        """
        根据查询匹配多个技能
        
        Args:
            query: 用户查询
            top_k: 返回前k个匹配结果
        
        Returns:
            List[Dict]: 匹配结果列表，包含skill_id和score
        """
        if not query or not self.skills:
            return []
        
        query_lower = query.lower()
        scores = []
        
        for skill in self.skills.values():
            score = 0
            
            for keyword in skill.metadata.keywords:
                keyword_lower = keyword.lower()
                if keyword_lower in query_lower:
                    score += 2
                elif any(k in keyword_lower for k in query_lower.split()):
                    score += 1
            
            if skill.metadata.name.lower() in query_lower:
                score += 3
            
            if score > 0:
                scores.append({
                    "skill_id": skill.metadata.skill_id,
                    "name": skill.metadata.name,
                    "score": score
                })
        
        # 按分数排序
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        return scores[:top_k]
    
    # =========================================================================
    # 技能执行资源（Level 3）
    # =========================================================================
    
    def get_skill_execution(
        self,
        skill_id: str,
        tools: Dict[str, Any],
        rules: List['Layer3Rule'],
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Optional[SkillExecution]:
        """
        获取技能执行资源（Level 3）
        
        在实际执行时调用，注入工具实例和规则。
        
        Args:
            skill_id: 技能ID
            tools: 工具实例映射（工具名 -> 工具实例）
            rules: Layer3规则列表
            user_profile: 用户档案
        
        Returns:
            SkillExecution或None
        
        Requirements: 8.1
        """
        skill = self.skills.get(skill_id)
        if not skill:
            logger.warning(f"⚠️ 技能不存在: {skill_id}")
            return None
        
        # 过滤出技能需要的工具
        required_tools = {}
        missing_tools = []
        
        for tool_name in skill.content.required_tools:
            if tool_name in tools:
                required_tools[tool_name] = tools[tool_name]
            else:
                missing_tools.append(tool_name)
        
        if missing_tools:
            logger.warning(f"⚠️ 技能 {skill_id} 缺少工具: {missing_tools}")
        
        # 添加可选工具
        for tool_name in skill.content.optional_tools:
            if tool_name in tools:
                required_tools[tool_name] = tools[tool_name]
        
        execution = SkillExecution(
            skill_id=skill_id,
            tools=required_tools,
            layer3_rules=rules,
            user_profile=user_profile
        )
        
        logger.info(
            f"🔧 创建技能执行资源: {skill_id}, "
            f"工具={len(required_tools)}/{len(skill.content.required_tools)}, "
            f"规则={len(rules)}"
        )
        
        return execution
    
    # =========================================================================
    # 技能查询方法
    # =========================================================================
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能"""
        return self.skills.get(skill_id)
    
    def get_skill_metadata(self, skill_id: str) -> Optional[SkillMetadata]:
        """获取技能元数据"""
        skill = self.skills.get(skill_id)
        return skill.metadata if skill else None
    
    def get_skill_content(self, skill_id: str) -> Optional[SkillContent]:
        """获取技能内容"""
        skill = self.skills.get(skill_id)
        return skill.content if skill else None
    
    def list_skills(self) -> List[str]:
        """列出所有技能ID"""
        return list(self.skills.keys())
    
    def list_skills_by_category(self, category: SkillCategory) -> List[str]:
        """按类别列出技能ID"""
        return [
            skill_id for skill_id, skill in self.skills.items()
            if skill.get_category() == category
        ]
    
    def get_skill_count(self) -> int:
        """获取技能总数"""
        return len(self.skills)
    
    # =========================================================================
    # 统计信息
    # =========================================================================
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取技能管理器统计信息
        
        Returns:
            Dict: 统计信息
        """
        # 按类别统计
        category_counts = {}
        for skill in self.skills.values():
            cat = skill.get_category().value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # 加载统计
        total_loads = sum(self._load_count.values())
        most_loaded = max(self._load_count.items(), key=lambda x: x[1]) if self._load_count else (None, 0)
        
        return {
            "total_skills": len(self.skills),
            "category_counts": category_counts,
            "loaded_skills_count": len(self._loaded_skills),
            "total_load_count": total_loads,
            "most_loaded_skill": most_loaded[0],
            "most_loaded_count": most_loaded[1],
            "estimated_system_prompt_tokens": self.estimate_system_prompt_tokens()
        }
    
    def get_load_statistics(self) -> Dict[str, int]:
        """获取技能加载统计"""
        return self._load_count.copy()


# =============================================================================
# 工厂函数
# =============================================================================

def create_skill_manager() -> SkillManager:
    """创建技能管理器实例"""
    return SkillManager()


def create_skill_manager_from_templates(
    templates: Dict[str, 'DAGTemplateDefinition']
) -> SkillManager:
    """
    从DAG模板创建技能管理器
    
    Args:
        templates: DAG模板字典
    
    Returns:
        SkillManager: 已注册技能的管理器
    """
    manager = SkillManager()
    manager.register_from_dag_templates(templates)
    return manager
