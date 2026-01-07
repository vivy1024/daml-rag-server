"""
训练反馈记录工具

记录用户的训练反馈，包括：
- 疲劳程度（1-10分）
- 主观感受（文本描述）
- 训练记录（动作、组数、次数、重量等）

这是前端训练记录功能的后端支持，只负责存储反馈数据，不进行自动评估。

@version 1.0.0
@date 2025-12-20
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field, validator
from datetime import datetime
import logging

from ..base_tool import BaseMCPTool

logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic模型定义
# ============================================================================

class TrainingRecord(BaseModel):
    """单条训练记录"""
    exercise_name: str = Field(..., description="动作名称")
    sets: int = Field(..., ge=1, description="组数")
    reps: int = Field(..., ge=1, description="次数")
    weight: float = Field(..., ge=0, description="重量（kg）")
    notes: Optional[str] = Field(None, description="备注")


class RecordTrainingFeedbackInput(BaseModel):
    """训练反馈记录输入"""
    user_id: str = Field(..., description="用户ID")
    session_id: str = Field(..., description="训练会话ID")
    fatigue_level: int = Field(..., ge=1, le=10, description="疲劳程度（1-10分）")
    subjective_feeling: str = Field(..., description="主观感受（文本描述）")
    training_records: List[TrainingRecord] = Field(..., min_items=1, description="训练记录列表")
    date: Optional[str] = Field(None, description="日期（ISO 8601格式，默认今天）")


class RecordTrainingFeedbackOutput(BaseModel):
    """训练反馈记录输出"""
    success: bool = Field(..., description="是否成功")
    tool_name: str = Field(..., description="工具名称")
    data: Dict[str, Any] = Field(..., description="反馈记录数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


# ============================================================================
# 工具实现
# ============================================================================

class RecordTrainingFeedback(BaseMCPTool):
    """
    训练反馈记录工具
    
    功能：
    1. 记录用户的训练反馈（疲劳程度、主观感受、训练记录）
    2. 存储到用户档案的training_feedback字段
    3. 支持前端训练记录界面的数据持久化
    
    特点：
    - 简单存储：只负责存储反馈数据，不进行自动评估
    - 前端驱动：数据由前端训练记录界面收集
    - 历史追踪：支持查询历史反馈记录
    """
    
    def get_name(self) -> str:
        return "record_training_feedback"
    
    def get_description(self) -> str:
        return """记录用户的训练反馈，包括疲劳程度（1-10分）、主观感受和训练记录。
        
这是前端训练记录功能的后端支持，只负责存储反馈数据，不进行自动评估。

输入参数：
- user_id: 用户ID
- session_id: 训练会话ID
- fatigue_level: 疲劳程度（1-10分）
- subjective_feeling: 主观感受（文本描述）
- training_records: 训练记录列表（动作、组数、次数、重量等）
- date: 日期（可选，默认今天）

返回数据：
- feedback_record: 反馈记录
- user_id: 用户ID
- message: 成功消息"""
    
    def get_category(self) -> str:
        return "training"
    
    def get_complexity(self) -> str:
        return "simple"
    
    def get_estimated_duration(self) -> float:
        return 500.0  # 500ms
    
    def requires_user_profile(self) -> bool:
        return True
    
    def get_dependencies(self) -> List[str]:
        return ["user_profile_mcp"]  # 依赖用户档案MCP服务
    
    def get_input_schema(self) -> type[BaseModel]:
        return RecordTrainingFeedbackInput
    
    def get_output_schema(self) -> type[BaseModel]:
        return RecordTrainingFeedbackOutput
    
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行训练反馈记录
        
        Args:
            input_data: 输入数据（已验证）
        
        Returns:
            标准化输出格式
        """
        try:
            user_id = input_data["user_id"]
            session_id = input_data["session_id"]
            fatigue_level = input_data["fatigue_level"]
            subjective_feeling = input_data["subjective_feeling"]
            training_records = input_data["training_records"]
            date = input_data.get("date") or datetime.now().isoformat()
            
            # 构建反馈记录
            feedback_record = {
                "session_id": session_id,
                "date": date,
                "fatigue_level": fatigue_level,
                "subjective_feeling": subjective_feeling,
                "training_records": training_records,
                "created_at": datetime.now().isoformat()
            }
            
            # 注意：实际存储需要通过MCP客户端调用 update_user_profile
            # 这里先返回成功，实际存储逻辑由MCPToolManager处理
            
            self.logger.info(
                f"✅ 训练反馈记录成功: user_id={user_id}, "
                f"session_id={session_id}, fatigue_level={fatigue_level}"
            )
            
            return {
                "success": True,
                "tool_name": self.get_name(),
                "data": {
                    "feedback_record": feedback_record,
                    "user_id": user_id,
                    "message": "训练反馈记录成功"
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ 记录训练反馈失败: {str(e)}")
            return {
                "success": False,
                "tool_name": self.get_name(),
                "error": {
                    "code": "RECORD_FEEDBACK_ERROR",
                    "message": f"记录训练反馈失败: {str(e)}",
                    "type": type(e).__name__
                }
            }
