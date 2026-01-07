"""
数据补充相关的数据模型
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class SupplementResult:
    """单个补充操作的结果"""
    total_nodes: int = 0
    updated_nodes: int = 0
    created_nodes: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    quality_report: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    
    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_nodes == 0:
            return 0.0
        return (self.updated_nodes + self.created_nodes) / self.total_nodes * 100
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0


@dataclass
class ValidationResult:
    """数据验证结果"""
    field_name: str
    total_checked: int = 0
    valid_count: int = 0
    invalid_count: int = 0
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def is_valid(self) -> bool:
        """是否全部有效"""
        return self.invalid_count == 0
    
    @property
    def validity_rate(self) -> float:
        """有效率"""
        if self.total_checked == 0:
            return 0.0
        return self.valid_count / self.total_checked * 100


@dataclass
class SupplementReport:
    """完整的数据补充报告"""
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # 各阶段结果
    exercise_result: Optional[SupplementResult] = None
    food_result: Optional[SupplementResult] = None
    injury_type_result: Optional[SupplementResult] = None
    rehab_phases_result: Optional[SupplementResult] = None
    rehab_progressions_result: Optional[SupplementResult] = None
    
    # 训练知识相关结果
    training_volume_result: Optional[SupplementResult] = None
    strength_standard_result: Optional[SupplementResult] = None
    workout_program_result: Optional[SupplementResult] = None
    acsm_standard_result: Optional[SupplementResult] = None
    nsca_standard_result: Optional[SupplementResult] = None
    
    # 验证结果
    validation_results: Dict[str, ValidationResult] = field(default_factory=dict)
    
    # 总体统计
    total_errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_result(self, stage: str, result: SupplementResult):
        """添加阶段结果"""
        if stage == "exercise":
            self.exercise_result = result
        elif stage == "food":
            self.food_result = result
        elif stage == "injury_type":
            self.injury_type_result = result
        elif stage == "rehab_phases":
            self.rehab_phases_result = result
        elif stage == "rehab_progressions":
            self.rehab_progressions_result = result
        elif stage == "training_volume":
            self.training_volume_result = result
        elif stage == "strength_standard":
            self.strength_standard_result = result
        elif stage == "workout_program":
            self.workout_program_result = result
        elif stage == "acsm_standard":
            self.acsm_standard_result = result
        elif stage == "nsca_standard":
            self.nsca_standard_result = result
        
        # 收集错误
        if result.has_errors:
            self.total_errors.extend(result.errors)
    
    def add_validation(self, field_name: str, result: ValidationResult):
        """添加验证结果"""
        self.validation_results[field_name] = result
        
        # 收集验证错误
        if not result.is_valid:
            self.total_errors.extend(result.errors)
    
    def finalize(self):
        """完成报告"""
        self.end_time = datetime.now()
    
    @property
    def total_execution_time(self) -> float:
        """总执行时间（秒）"""
        if self.end_time is None:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.total_errors) > 0
    
    @property
    def is_successful(self) -> bool:
        """是否全部成功"""
        return not self.has_errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result_dict = {
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "execution_time_seconds": self.total_execution_time,
            "exercise": {
                "total_nodes": self.exercise_result.total_nodes if self.exercise_result else 0,
                "updated_nodes": self.exercise_result.updated_nodes if self.exercise_result else 0,
                "success_rate": self.exercise_result.success_rate if self.exercise_result else 0,
                "errors": self.exercise_result.errors if self.exercise_result else []
            } if self.exercise_result else None,
            "food": {
                "total_nodes": self.food_result.total_nodes if self.food_result else 0,
                "updated_nodes": self.food_result.updated_nodes if self.food_result else 0,
                "success_rate": self.food_result.success_rate if self.food_result else 0,
                "errors": self.food_result.errors if self.food_result else []
            } if self.food_result else None,
            "injury_type": {
                "total_nodes": self.injury_type_result.total_nodes if self.injury_type_result else 0,
                "updated_nodes": self.injury_type_result.updated_nodes if self.injury_type_result else 0,
                "success_rate": self.injury_type_result.success_rate if self.injury_type_result else 0,
                "errors": self.injury_type_result.errors if self.injury_type_result else []
            } if self.injury_type_result else None,
            "rehab_phases": {
                "created_nodes": self.rehab_phases_result.created_nodes if self.rehab_phases_result else 0,
                "errors": self.rehab_phases_result.errors if self.rehab_phases_result else []
            } if self.rehab_phases_result else None,
            "rehab_progressions": {
                "created_nodes": self.rehab_progressions_result.created_nodes if self.rehab_progressions_result else 0,
                "errors": self.rehab_progressions_result.errors if self.rehab_progressions_result else []
            } if self.rehab_progressions_result else None,
            "training_volume": {
                "total_nodes": self.training_volume_result.total_nodes if self.training_volume_result else 0,
                "updated_nodes": self.training_volume_result.updated_nodes if self.training_volume_result else 0,
                "success_rate": self.training_volume_result.success_rate if self.training_volume_result else 0,
                "errors": self.training_volume_result.errors if self.training_volume_result else []
            } if self.training_volume_result else None,
            "strength_standard": {
                "total_nodes": self.strength_standard_result.total_nodes if self.strength_standard_result else 0,
                "created_nodes": self.strength_standard_result.created_nodes if self.strength_standard_result else 0,
                "errors": self.strength_standard_result.errors if self.strength_standard_result else []
            } if self.strength_standard_result else None,
            "workout_program": {
                "total_nodes": self.workout_program_result.total_nodes if self.workout_program_result else 0,
                "created_nodes": self.workout_program_result.created_nodes if self.workout_program_result else 0,
                "errors": self.workout_program_result.errors if self.workout_program_result else []
            } if self.workout_program_result else None,
            "acsm_standard": {
                "total_nodes": self.acsm_standard_result.total_nodes if self.acsm_standard_result else 0,
                "created_nodes": self.acsm_standard_result.created_nodes if self.acsm_standard_result else 0,
                "errors": self.acsm_standard_result.errors if self.acsm_standard_result else []
            } if self.acsm_standard_result else None,
            "nsca_standard": {
                "total_nodes": self.nsca_standard_result.total_nodes if self.nsca_standard_result else 0,
                "created_nodes": self.nsca_standard_result.created_nodes if self.nsca_standard_result else 0,
                "errors": self.nsca_standard_result.errors if self.nsca_standard_result else []
            } if self.nsca_standard_result else None,
            "validation": {
                field: {
                    "total_checked": result.total_checked,
                    "valid_count": result.valid_count,
                    "invalid_count": result.invalid_count,
                    "validity_rate": result.validity_rate,
                    "errors": result.errors
                }
                for field, result in self.validation_results.items()
            },
            "total_errors": len(self.total_errors),
            "is_successful": self.is_successful
        }
        return result_dict
    
    def generate_summary(self) -> str:
        """生成摘要报告"""
        lines = [
            "=" * 60,
            "Neo4j数据补充执行报告",
            "=" * 60,
            f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}",
            f"结束时间: {self.end_time.strftime('%Y-%m-%d %H:%M:%S') if self.end_time else '进行中'}",
            f"执行时长: {self.total_execution_time:.2f}秒",
            "",
            "数据补充结果:",
            "-" * 60,
        ]
        
        if self.exercise_result:
            lines.extend([
                f"Exercise节点: {self.exercise_result.updated_nodes}/{self.exercise_result.total_nodes} "
                f"({self.exercise_result.success_rate:.1f}%)"
            ])
        
        if self.food_result:
            lines.extend([
                f"Food节点: {self.food_result.updated_nodes}/{self.food_result.total_nodes} "
                f"({self.food_result.success_rate:.1f}%)"
            ])
        
        if self.injury_type_result:
            lines.extend([
                f"InjuryType节点: {self.injury_type_result.updated_nodes}/{self.injury_type_result.total_nodes} "
                f"({self.injury_type_result.success_rate:.1f}%)"
            ])
        
        if self.rehab_phases_result:
            lines.extend([
                f"RehabilitationPhase节点: {self.rehab_phases_result.created_nodes}个已创建"
            ])
        
        if self.rehab_progressions_result:
            lines.extend([
                f"REHAB_PROGRESSION关系: {self.rehab_progressions_result.created_nodes}个已创建"
            ])
        
        # 训练知识相关结果
        if self.training_volume_result:
            lines.extend([
                f"训练量标准: {self.training_volume_result.updated_nodes}/{self.training_volume_result.total_nodes} "
                f"({self.training_volume_result.success_rate:.1f}%)"
            ])
        
        if self.strength_standard_result:
            lines.extend([
                f"力量标准: {self.strength_standard_result.created_nodes}个已创建"
            ])
        
        if self.workout_program_result:
            lines.extend([
                f"训练计划模板: {self.workout_program_result.created_nodes}个已创建"
            ])
        
        if self.acsm_standard_result:
            lines.extend([
                f"ACSM标准: {self.acsm_standard_result.created_nodes}个已创建"
            ])
        
        if self.nsca_standard_result:
            lines.extend([
                f"NSCA标准: {self.nsca_standard_result.created_nodes}个已创建"
            ])
        
        if self.validation_results:
            lines.extend([
                "",
                "数据验证结果:",
                "-" * 60,
            ])
            for field, result in self.validation_results.items():
                status = "✅" if result.is_valid else "❌"
                lines.append(
                    f"{status} {field}: {result.valid_count}/{result.total_checked} "
                    f"({result.validity_rate:.1f}%)"
                )
        
        lines.extend([
            "",
            "=" * 60,
            f"总体状态: {'✅ 成功' if self.is_successful else '❌ 有错误'}",
            f"错误数量: {len(self.total_errors)}",
            "=" * 60,
        ])
        
        return "\n".join(lines)
