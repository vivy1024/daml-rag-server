"""
动作模式平衡器 - MCP工具

功能特性：
- 基于Muscle节点数据
- 使用synergy_partners和antagonist_partners字段
- 使用USES_FORCE关系分析推拉平衡（v8.61.0新增）
- 分析训练计划平衡性
- 提供程序调整建议

作者: BUILD_BODY Team
版本: v2.2.0
更新: 2026-01-06 - 添加USES_FORCE关系支持
"""

from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field
import time
from datetime import datetime

from ...mcp_tools.base_tool import BaseMCPTool


class MovementPatternBalancerInput(BaseModel):
    """动作模式平衡器输入Schema"""
    user_id: str = Field(..., description="用户ID")
    current_program: List[str] = Field(..., description="当前计划的动作ID列表")
    target_muscle_groups: List[str] = Field(..., description="目标肌群列表")


class ForceTypeBalance(BaseModel):
    """推拉平衡分析结果"""
    push_count: int = Field(0, description="推类动作数量")
    pull_count: int = Field(0, description="拉类动作数量")
    hold_count: int = Field(0, description="保持类动作数量")
    push_pull_ratio: float = Field(0.0, description="推拉比例")
    is_balanced: bool = Field(False, description="是否平衡")
    recommendation: str = Field("", description="平衡建议")


class BalanceAnalysis(BaseModel):
    """平衡分析结果"""
    balanced_score: float = Field(..., description="平衡分数（0-1）")
    imbalanced_patterns: List[str] = Field(..., description="不平衡模式列表")
    synergy_coverage: Dict[str, List[str]] = Field(..., description="协同肌群覆盖情况")
    antagonist_balance: Dict[str, str] = Field(..., description="拮抗肌群平衡情况")
    force_type_balance: Optional[ForceTypeBalance] = Field(None, description="推拉平衡分析")
    adjustment_suggestions: List[str] = Field(..., description="调整建议")


class MovementPatternBalancerOutput(BaseModel):
    """动作模式平衡器输出Schema"""
    success: bool
    tool_name: str
    balance_analysis: BalanceAnalysis
    program_adjustments: List[str]
    execution_time_ms: float
    confidence_score: Optional[float] = None


class MovementPatternBalancer(BaseMCPTool):
    """动作模式平衡器工具"""
    
    def get_name(self) -> str:
        return "movement_pattern_balancer"
    
    def get_description(self) -> str:
        return "动作模式平衡器 - 分析训练计划的肌群平衡性，基于协同和拮抗肌群关系提供调整建议"
    
    def get_category(self) -> str:
        return "training"
    
    def get_input_schema(self) -> type[BaseModel]:
        return MovementPatternBalancerInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return MovementPatternBalancerOutput
    
    def get_complexity(self) -> str:
        return "complex"
    
    def get_estimated_duration(self) -> float:
        return 600.0  # 600ms
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行动作模式平衡分析
        
        流程：
        1. 验证参数
        2. 查询当前计划涉及的动作
        3. 获取肌群协同关系
        4. 分析推拉平衡（使用USES_FORCE关系）
        5. 分析平衡性
        6. 生成调整建议
        """
        start_time = time.time()
        
        try:
            # 1. 验证参数
            self._validate_params(input_data)
            
            user_id = input_data.get("user_id")
            current_program = input_data.get("current_program", [])
            target_muscle_groups = input_data.get("target_muscle_groups", [])
            
            # 2. 查询当前计划涉及的动作（包含力类型）
            exercises = await self._get_exercises_in_program(current_program)
            
            # 3. 获取肌群协同关系
            synergy_relations = await self._get_muscle_synergy_relations(target_muscle_groups)
            
            # 4. 分析推拉平衡（使用USES_FORCE关系）
            force_type_balance = await self._analyze_force_type_balance(current_program)
            
            # 5. 分析平衡性
            balance_analysis = await self._analyze_balance(
                exercises, synergy_relations, force_type_balance
            )
            
            # 6. 生成调整建议
            adjustments = self._generate_adjustments(balance_analysis, target_muscle_groups)
            
            execution_time_ms = (time.time() - start_time) * 1000
            
            result = {
                "success": True,
                "tool_name": self.get_name(),
                "balance_analysis": {
                    "balanced_score": balance_analysis["balanced_score"],
                    "imbalanced_patterns": balance_analysis["imbalanced_patterns"],
                    "synergy_coverage": balance_analysis["synergy_coverage"],
                    "antagonist_balance": balance_analysis["antagonist_balance"],
                    "force_type_balance": balance_analysis.get("force_type_balance"),
                    "adjustment_suggestions": balance_analysis["adjustment_suggestions"]
                },
                "program_adjustments": adjustments,
                "execution_time_ms": execution_time_ms,
                "confidence_score": 88.0  # 提升置信度，因为使用了更多数据
            }
            
            self.logger.info(
                f"✅ 动作模式平衡分析完成: 平衡分数 {balance_analysis['balanced_score']:.2f}, "
                f"推拉比例 {balance_analysis.get('force_type_balance', {}).get('push_pull_ratio', 0):.2f}"
            )
            
            return result
            
        except Exception as e:
            execution_time_ms = (time.time() - start_time) * 1000
            self.logger.error(f"❌ 动作模式平衡分析执行失败: {e}", exc_info=True)
            
            return {
                "success": False,
                "tool_name": self.get_name(),
                "balance_analysis": {
                    "balanced_score": 0.0,
                    "imbalanced_patterns": [],
                    "synergy_coverage": {},
                    "antagonist_balance": {},
                    "force_type_balance": None,
                    "adjustment_suggestions": []
                },
                "program_adjustments": [],
                "execution_time_ms": execution_time_ms,
                "confidence_score": 0.0
            }
    
    def _validate_params(self, params: Dict[str, Any]) -> None:
        """验证参数（对齐TypeScript版本）"""
        if "current_program" not in params:
            raise ValueError("缺少参数: current_program")
    
    async def _get_exercises_in_program(self, exercise_ids: List[str]) -> List[Dict[str, Any]]:
        """获取计划中的动作（对齐TypeScript版本）"""
        if not exercise_ids:
            return []
        
        # 注意：Neo4j Exercise节点使用 id 字段，不是 exercise_id
        query = """
        MATCH (e:Exercise)
        WHERE e.id IN $exercise_ids
        OPTIONAL MATCH (e)-[:TARGETS_PRIMARY]->(m:Muscle)
        RETURN e, collect(DISTINCT m.name_zh) as target_muscles
        """
        
        results = await self.neo4j_client.execute_query(query, {"exercise_ids": exercise_ids})
        return results
    
    async def _get_muscle_synergy_relations(
        self, 
        muscle_groups: List[str]
    ) -> Dict[str, Dict[str, List[str]]]:
        """获取肌群协同关系（对齐TypeScript版本）"""
        query = """
        MATCH (m:Muscle)
        WHERE m.name_zh IN $muscle_groups
        RETURN
            m.name_zh as muscle,
            m.synergy_partners,
            m.antagonist_partners
        """
        
        results = await self.neo4j_client.execute_query(query, {"muscle_groups": muscle_groups})
        relations = {}
        
        for result in results:
            relations[result["muscle"]] = {
                "synergy": result.get("synergy_partners") or [],
                "antagonist": result.get("antagonist_partners") or []
            }
        
        return relations
    
    async def _analyze_force_type_balance(
        self,
        exercise_ids: List[str]
    ) -> Dict[str, Any]:
        """
        分析推拉平衡（使用USES_FORCE关系）
        
        v8.61.0新增：利用Neo4j的USES_FORCE关系分析训练计划的推拉平衡
        
        Args:
            exercise_ids: 动作ID列表
            
        Returns:
            推拉平衡分析结果
        """
        if not exercise_ids:
            return {
                "push_count": 0,
                "pull_count": 0,
                "hold_count": 0,
                "push_pull_ratio": 0.0,
                "is_balanced": False,
                "recommendation": "训练计划为空"
            }
        
        # 使用USES_FORCE关系查询每个动作的力类型
        query = """
        MATCH (e:Exercise)-[:USES_FORCE]->(f:ForceType)
        WHERE e.id IN $exercise_ids
        RETURN f.name as force_type, count(e) as count
        """
        
        results = await self.neo4j_client.execute_query(query, {"exercise_ids": exercise_ids})
        
        # 统计各类型数量
        push_count = 0
        pull_count = 0
        hold_count = 0
        
        for result in results:
            force_type = result.get("force_type", "")
            count = result.get("count", 0)
            
            if force_type == "push":
                push_count = count
            elif force_type == "pull":
                pull_count = count
            elif force_type == "hold":
                hold_count = count
        
        # 计算推拉比例
        total_push_pull = push_count + pull_count
        if total_push_pull > 0:
            push_pull_ratio = push_count / total_push_pull
        else:
            push_pull_ratio = 0.5  # 默认平衡
        
        # 判断是否平衡（理想比例为1:1，允许0.4-0.6的范围）
        is_balanced = 0.4 <= push_pull_ratio <= 0.6
        
        # 生成建议
        if push_pull_ratio > 0.6:
            recommendation = f"推类动作过多（{push_count}个），建议增加拉类动作以平衡"
        elif push_pull_ratio < 0.4:
            recommendation = f"拉类动作过多（{pull_count}个），建议增加推类动作以平衡"
        else:
            recommendation = f"推拉平衡良好（推{push_count}:拉{pull_count}）"
        
        return {
            "push_count": push_count,
            "pull_count": pull_count,
            "hold_count": hold_count,
            "push_pull_ratio": round(push_pull_ratio, 2),
            "is_balanced": is_balanced,
            "recommendation": recommendation
        }
    
    async def _analyze_balance(
        self,
        exercises: List[Dict[str, Any]],
        synergy_relations: Dict[str, Dict[str, List[str]]],
        force_type_balance: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """分析平衡性（增强版：包含推拉平衡）"""
        # 提取所有目标肌群
        all_muscles: Set[str] = set()
        for exercise in exercises:
            target_muscles = exercise.get("target_muscles", [])
            all_muscles.update(target_muscles)
        
        # 计算基础平衡分数
        base_score = self._calculate_balance_score(all_muscles, synergy_relations)
        
        # 如果有推拉平衡数据，综合计算
        if force_type_balance and force_type_balance.get("is_balanced") is not None:
            force_balance_score = 1.0 if force_type_balance["is_balanced"] else 0.5
            # 综合评分：肌群平衡60% + 推拉平衡40%
            balance_score = base_score * 0.6 + force_balance_score * 0.4
        else:
            balance_score = base_score
        
        # 识别不平衡模式
        imbalanced_patterns = self._identify_imbalanced_patterns(all_muscles, synergy_relations)
        
        # 添加推拉不平衡模式
        if force_type_balance and not force_type_balance.get("is_balanced", True):
            imbalanced_patterns.append(f"推拉不平衡: {force_type_balance.get('recommendation', '')}")
        
        # 计算协同覆盖
        synergy_coverage = {}
        for muscle in all_muscles:
            synergy_coverage[muscle] = synergy_relations.get(muscle, {}).get("synergy", [])
        
        # 计算拮抗平衡
        antagonist_balance = self._calculate_antagonist_balance(synergy_relations)
        
        return {
            "balanced_score": round(balance_score, 2),
            "imbalanced_patterns": imbalanced_patterns,
            "synergy_coverage": synergy_coverage,
            "antagonist_balance": antagonist_balance,
            "force_type_balance": force_type_balance,
            "adjustment_suggestions": []
        }
    
    def _calculate_balance_score(
        self,
        muscles: Set[str],
        relations: Dict[str, Dict[str, List[str]]]
    ) -> float:
        """计算平衡分数（对齐TypeScript版本）"""
        if not muscles:
            return 0.0
        
        score = 0.0
        total = len(muscles)
        
        for muscle in muscles:
            relation = relations.get(muscle)
            if relation:
                synergy_count = len(relation.get("synergy", []))
                antagonist_count = len(relation.get("antagonist", []))
                # 平衡的肌群应该有合理的协同和拮抗关系
                if synergy_count > 0 and antagonist_count > 0:
                    score += 1.0
        
        return score / total if total > 0 else 0.0
    
    def _identify_imbalanced_patterns(
        self,
        muscles: Set[str],
        relations: Dict[str, Dict[str, List[str]]]
    ) -> List[str]:
        """识别不平衡模式（对齐TypeScript版本）"""
        patterns = []
        
        for muscle in muscles:
            if muscle not in relations:
                patterns.append(f"{muscle}: 缺乏协同关系数据")
                continue
            
            relation = relations[muscle]
            if not relation:
                patterns.append(f"{muscle}: 缺乏关系数据")
                continue
            
            synergy = relation.get("synergy", [])
            antagonist = relation.get("antagonist", [])
            
            if not synergy:
                patterns.append(f"{muscle}: 缺乏协同肌群训练")
            if len(antagonist) < len(synergy) * 0.5:
                patterns.append(f"{muscle}: 拮抗肌群训练不足")
        
        return patterns
    
    def _calculate_antagonist_balance(
        self,
        relations: Dict[str, Dict[str, List[str]]]
    ) -> Dict[str, str]:
        """计算拮抗平衡（对齐TypeScript版本）"""
        balance = {}
        
        for muscle, data in relations.items():
            antagonists = data.get("antagonist", [])
            if antagonists:
                # 检查拮抗肌群是否也有合理的拮抗关系
                first_antagonist = antagonists[0]  # 只检查第一个拮抗肌群
                if (first_antagonist in relations and 
                    muscle in relations[first_antagonist].get("antagonist", [])):
                    balance[muscle] = f"与{first_antagonist}平衡"
                else:
                    balance[muscle] = f"与{first_antagonist}不平衡"
        
        return balance
    
    def _generate_adjustments(
        self,
        analysis: Dict[str, Any],
        target_muscles: List[str]
    ) -> List[str]:
        """生成调整建议（对齐TypeScript版本）"""
        adjustments = []
        
        if analysis["balanced_score"] < 0.7:
            adjustments.append("整体平衡性偏低，建议增加拮抗肌群训练")
        
        for pattern in analysis["imbalanced_patterns"]:
            if "缺乏协同" in pattern:
                muscle = pattern.split(":")[0]
                adjustments.append(f"为{muscle}增加协同肌群训练")
            elif "拮抗肌群训练不足" in pattern:
                muscle = pattern.split(":")[0]
                adjustments.append(f"加强{muscle}的拮抗肌群训练")
        
        adjustments.extend([
            "确保推拉动作平衡",
            "注意上下肢比例",
            "定期评估和调整训练计划"
        ])
        
        return adjustments
