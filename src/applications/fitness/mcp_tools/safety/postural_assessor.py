"""
体态评估工具 MCP Tool

功能特性：
- 识别用户的体态问题
- 推荐矫正动作（基于CORRECTS关系）
- 警告加重动作（基于AGGRAVATES关系）
- 提供相关肌肉信息（基于RELATED_TO关系）

作者: BUILD_BODY Team
版本: v1.0.0
日期: 2026-01-05
Requirements: 20.5, 20.6
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import time

from ..base_tool import BaseMCPTool


# =============================================================================
# 输入Schema定义
# =============================================================================

class PosturalAssessorInput(BaseModel):
    """体态评估工具输入Schema"""
    user_id: str = Field(..., description="用户ID，用于获取体态问题")
    postural_issues: Optional[List[str]] = Field(
        None, 
        description="体态问题列表（中文），如果不提供则从用户档案读取"
    )
    include_exercises: bool = Field(
        True, 
        description="是否包含矫正和加重动作列表"
    )
    max_exercises_per_issue: int = Field(
        5, 
        description="每个体态问题返回的最大动作数量"
    )


# =============================================================================
# 输出类型定义
# =============================================================================

class RelatedMuscle(BaseModel):
    """相关肌肉"""
    name: str
    name_zh: str
    description: Optional[str] = None



class CorrectiveExercise(BaseModel):
    """矫正动作"""
    exercise_id: str
    name: str
    name_zh: str
    category: str
    difficulty: str
    description: Optional[str] = None


class AggravatingExercise(BaseModel):
    """加重动作"""
    exercise_id: str
    name: str
    name_zh: str
    category: str
    risk_level: str
    warning: str


class PosturalIssueAssessment(BaseModel):
    """单个体态问题评估"""
    issue_name: str
    issue_name_zh: str
    category: str
    description: str
    
    # 相关肌肉
    related_muscles: List[RelatedMuscle]
    
    # 矫正动作
    corrective_exercises: List[CorrectiveExercise]
    corrective_count: int
    
    # 加重动作
    aggravating_exercises: List[AggravatingExercise]
    aggravating_count: int
    
    # 建议
    recommendations: List[str]


class PosturalAssessorOutput(BaseModel):
    """体态评估工具输出Schema"""
    success: bool
    tool_name: str
    user_id: str
    assessment_date: str
    
    # 评估结果
    total_issues: int
    issues_assessed: List[PosturalIssueAssessment]
    
    # 总体建议
    overall_recommendations: List[str]
    priority_issues: List[str]
    
    # 元数据
    execution_time_ms: float
    data_source: str



# =============================================================================
# MCP工具实现
# =============================================================================

class PosturalAssessor(BaseMCPTool):
    """体态评估工具"""
    
    name = "postural_assessor"
    description = "评估用户体态问题，推荐矫正动作并警告加重动作"
    input_schema = PosturalAssessorInput
    
    async def execute(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行体态评估
        
        Args:
            params: 输入参数
            
        Returns:
            评估结果
        """
        start_time = time.time()
        
        # 验证输入
        input_data = self.input_schema(**params)
        
        # 获取用户体态问题
        postural_issues = input_data.postural_issues
        if not postural_issues:
            # 从用户档案读取（优先使用DAG注入的user_profile）
            user_profile = params.get("user_profile") or await self._get_user_profile(input_data.user_id)
            postural_issues = user_profile.get("health_status", {}).get("postural_issues", [])
        
        if not postural_issues or postural_issues == ["无"]:
            return PosturalAssessorOutput(
                success=True,
                tool_name=self.name,
                user_id=input_data.user_id,
                assessment_date=datetime.now().isoformat(),
                total_issues=0,
                issues_assessed=[],
                overall_recommendations=["未检测到体态问题，保持良好的训练姿势"],
                priority_issues=[],
                execution_time_ms=(time.time() - start_time) * 1000,
                data_source="Neo4j PosturalIssue"
            ).dict()
        
        # 评估每个体态问题
        issues_assessed = []
        for issue_zh in postural_issues:
            if issue_zh == "无":
                continue
                
            assessment = await self._assess_postural_issue(
                issue_zh,
                input_data.include_exercises,
                input_data.max_exercises_per_issue
            )
            
            if assessment:
                issues_assessed.append(assessment)
        
        # 生成总体建议
        overall_recommendations = self._generate_overall_recommendations(issues_assessed)
        priority_issues = self._identify_priority_issues(issues_assessed)
        
        execution_time = (time.time() - start_time) * 1000
        
        return PosturalAssessorOutput(
            success=True,
            tool_name=self.name,
            user_id=input_data.user_id,
            assessment_date=datetime.now().isoformat(),
            total_issues=len(issues_assessed),
            issues_assessed=issues_assessed,
            overall_recommendations=overall_recommendations,
            priority_issues=priority_issues,
            execution_time_ms=execution_time,
            data_source="Neo4j PosturalIssue"
        ).dict()
    
    async def _assess_postural_issue(
        self,
        issue_zh: str,
        include_exercises: bool,
        max_exercises: int
    ) -> Optional[PosturalIssueAssessment]:
        """评估单个体态问题"""
        from applications.fitness.services.user_profile_data_mapper import UserProfileDataMapper
        
        # 映射到Neo4j节点名称
        issue_name = UserProfileDataMapper.POSTURAL_ISSUE_NAME_MAPPING.get(issue_zh)
        if not issue_name:
            return None
        
        # 查询体态问题节点信息
        query = """
        MATCH (p:PosturalIssue {name: $issue_name})
        RETURN p.name as name,
               p.name_zh as name_zh,
               p.category as category,
               p.description as description
        """
        result = self.neo4j_client.execute_query(query, {"issue_name": issue_name})
        
        if not result:
            return None
        
        issue_info = result[0]
        
        # 查询相关肌肉
        related_muscles = await self._get_related_muscles(issue_name)
        
        # 查询矫正动作和加重动作
        corrective_exercises = []
        aggravating_exercises = []
        
        if include_exercises:
            corrective_exercises = await self._get_corrective_exercises(
                issue_name, max_exercises
            )
            aggravating_exercises = await self._get_aggravating_exercises(
                issue_name, max_exercises
            )
        
        # 生成建议
        recommendations = self._generate_recommendations(
            issue_zh,
            len(corrective_exercises),
            len(aggravating_exercises)
        )
        
        return PosturalIssueAssessment(
            issue_name=issue_info["name"],
            issue_name_zh=issue_info["name_zh"],
            category=issue_info["category"],
            description=issue_info["description"],
            related_muscles=related_muscles,
            corrective_exercises=corrective_exercises,
            corrective_count=len(corrective_exercises),
            aggravating_exercises=aggravating_exercises,
            aggravating_count=len(aggravating_exercises),
            recommendations=recommendations
        )
    
    async def _get_related_muscles(self, issue_name: str) -> List[RelatedMuscle]:
        """获取相关肌肉"""
        query = """
        MATCH (p:PosturalIssue {name: $issue_name})-[:RELATED_TO]->(m:Muscle)
        RETURN m.name as name,
               m.name_zh as name_zh,
               m.description as description
        LIMIT 10
        """
        results = self.neo4j_client.execute_query(query, {"issue_name": issue_name})
        
        return [
            RelatedMuscle(
                name=r["name"],
                name_zh=r["name_zh"],
                description=r.get("description")
            )
            for r in results
        ]
    
    async def _get_corrective_exercises(
        self, issue_name: str, max_count: int
    ) -> List[CorrectiveExercise]:
        """获取矫正动作"""
        query = """
        MATCH (e:Exercise)-[:CORRECTS]->(p:PosturalIssue {name: $issue_name})
        RETURN e.id as exercise_id,
               e.name as name,
               e.name_zh as name_zh,
               e.category as category,
               e.difficulty_zh as difficulty,
               e.description as description
        ORDER BY e.difficulty_zh
        LIMIT $max_count
        """
        results = self.neo4j_client.execute_query(
            query, 
            {"issue_name": issue_name, "max_count": max_count}
        )
        
        return [
            CorrectiveExercise(
                exercise_id=str(r["exercise_id"]),
                name=r["name"],
                name_zh=r["name_zh"],
                category=r["category"],
                difficulty=r["difficulty"],
                description=r.get("description")
            )
            for r in results
        ]
    
    async def _get_aggravating_exercises(
        self, issue_name: str, max_count: int
    ) -> List[AggravatingExercise]:
        """获取加重动作"""
        query = """
        MATCH (e:Exercise)-[:AGGRAVATES]->(p:PosturalIssue {name: $issue_name})
        RETURN e.id as exercise_id,
               e.name as name,
               e.name_zh as name_zh,
               e.category as category,
               e.safety_level as risk_level
        LIMIT $max_count
        """
        results = self.neo4j_client.execute_query(
            query,
            {"issue_name": issue_name, "max_count": max_count}
        )
        
        return [
            AggravatingExercise(
                exercise_id=str(r["exercise_id"]),
                name=r["name"],
                name_zh=r["name_zh"],
                category=r["category"],
                risk_level=r.get("risk_level", "MODERATE"),
                warning=f"此动作可能加重{issue_name}问题，建议避免或在专业指导下进行"
            )
            for r in results
        ]
    
    def _generate_recommendations(
        self,
        issue_zh: str,
        corrective_count: int,
        aggravating_count: int
    ) -> List[str]:
        """生成针对性建议"""
        recommendations = []
        
        if corrective_count > 0:
            recommendations.append(
                f"建议每周进行2-3次矫正训练，每次选择2-3个矫正动作"
            )
            recommendations.append(
                f"矫正动作应使用轻负重，注重动作质量和肌肉感受"
            )
        else:
            recommendations.append(
                f"暂无针对{issue_zh}的矫正动作数据，建议咨询专业康复师"
            )
        
        if aggravating_count > 0:
            recommendations.append(
                f"训练中应避免或谨慎进行可能加重问题的动作"
            )
        
        # 根据体态问题类型添加特定建议
        if "圆肩" in issue_zh or "驼背" in issue_zh:
            recommendations.append("加强上背部肌肉训练，拉伸胸部肌肉")
        elif "骨盆" in issue_zh:
            recommendations.append("加强核心稳定性训练，改善骨盆位置")
        elif "膝" in issue_zh:
            recommendations.append("加强臀部和大腿肌肉力量，改善膝关节稳定性")
        
        return recommendations
    
    def _generate_overall_recommendations(
        self, issues: List[PosturalIssueAssessment]
    ) -> List[str]:
        """生成总体建议"""
        if not issues:
            return ["保持良好的训练姿势和生活习惯"]
        
        recommendations = [
            f"检测到{len(issues)}个体态问题，建议制定系统的矫正训练计划",
            "矫正训练应循序渐进，避免急于求成",
            "建议在专业教练或康复师指导下进行矫正训练",
            "日常生活中注意保持正确姿势，避免长时间保持不良姿势"
        ]
        
        # 如果有多个问题，建议优先处理
        if len(issues) > 2:
            recommendations.append("建议优先处理影响最大的体态问题，逐步改善")
        
        return recommendations
    
    def _identify_priority_issues(
        self, issues: List[PosturalIssueAssessment]
    ) -> List[str]:
        """识别优先处理的体态问题"""
        # 根据加重动作数量和类别判断优先级
        priority = []
        
        for issue in issues:
            # 脊柱相关问题优先级最高
            if issue.category == "spine":
                priority.append(issue.issue_name_zh)
            # 加重动作较多的问题优先级较高
            elif issue.aggravating_count > 3:
                priority.append(issue.issue_name_zh)
        
        return priority[:3]  # 最多返回3个优先问题
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """获取用户档案"""
        # 方式1: 通过BaseMCPTool注入的backend_client
        if hasattr(self, 'backend_client') and self.backend_client:
            try:
                profile = await self.backend_client.get_user_profile(user_id)
                if profile:
                    return profile
            except Exception as e:
                self.logger.warning(f"Backend client获取用户档案失败: {e}")

        # 方式2: 通过user_profile_provider
        if hasattr(self, 'user_profile_provider') and self.user_profile_provider:
            try:
                profile = await self.user_profile_provider(user_id)
                if profile:
                    return profile
            except Exception as e:
                self.logger.warning(f"User profile provider获取用户档案失败: {e}")

        # Fallback: 返回空字典
        self.logger.info(f"无可用的用户档案获取方式，返回空档案: user_id={user_id}")
        return {}


# 注册工具
def register_tool():
    """注册体态评估工具"""
    from ..registry import register_mcp_tool
    register_mcp_tool(PosturalAssessor)
