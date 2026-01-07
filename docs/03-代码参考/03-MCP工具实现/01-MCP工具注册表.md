# 核心组件：MCP工具注册表代码参考

**版本**: v1.0.0  
**创建日期**: 2025-12-17  
**状态**: ✅ 已完成

---

## 概述

MCP工具注册表负责管理15个Python内置MCP工具的注册、查找和调用。

### 文件位置

- **主文件**: `src/applications/fitness/mcp_tools/registry.py`
- **工具初始化**: `src/applications/fitness/mcp_tools/__init__.py`
- **工具目录**: `src/applications/fitness/mcp_tools/`

### 核心类：MCPToolRegistry

```python
class MCPToolRegistry:
    """
    MCP工具注册表
    
    职责：
    - 注册Python内置MCP工具
    - 提供工具查找和调用接口
    - 管理工具元数据
    """
    
    def __init__(self):
        self.tools: Dict[str, Callable] = {}
        self.tool_metadata: Dict[str, Dict[str, Any]] = {}
    
    def register_tool(
        self,
        name: str,
        func: Callable,
        metadata: Dict[str, Any]
    ):
        """
        注册工具
        
        Args:
            name: 工具名称
            func: 工具函数
            metadata: 工具元数据（描述、参数、返回值）
        """
        self.tools[name] = func
        self.tool_metadata[name] = metadata
        logger.info(f"注册MCP工具: {name}")
    
    async def call_tool(
        self,
        name: str,
        arguments: Dict[str, Any]
    ) -> Any:
        """
        调用工具
        
        Args:
            name: 工具名称
            arguments: 工具参数
            
        Returns:
            工具执行结果
        """
        if name not in self.tools:
            raise ToolNotFoundError(f"工具不存在: {name}")
        
        tool_func = self.tools[name]
        
        try:
            result = await tool_func(**arguments)
            return result
        except Exception as e:
            logger.error(f"工具调用失败: {name}, 错误: {e}")
            raise ToolExecutionError(f"工具执行失败: {e}")
```

### 工具初始化

```python
# src/applications/fitness/mcp_tools/__init__.py

def initialize_all_tools(registry: MCPToolRegistry):
    """
    初始化所有MCP工具
    
    注册15个Python内置工具：
    - 5个P0核心工具
    - 8个P1建议工具
    - 2个P2扩展工具
    """
    # P0核心工具
    from .exercise import intelligent_exercise_selector
    from .safety import contraindications_checker, injury_risk_assessor
    from .training import muscle_group_volume_calculator, professional_program_designer
    
    registry.register_tool(
        "intelligent_exercise_selector",
        intelligent_exercise_selector.execute,
        intelligent_exercise_selector.METADATA
    )
    
    registry.register_tool(
        "contraindications_checker",
        contraindications_checker.execute,
        contraindications_checker.METADATA
    )
    
    # ... 注册其他13个工具
    
    logger.info(f"已注册{len(registry.tools)}个MCP工具")
```

---

## 15个MCP工具清单

### P0核心工具（5个）

1. **intelligent_exercise_selector** - 智能动作选择
2. **contraindications_checker** - 禁忌症检查
3. **injury_risk_assessor** - 损伤风险评估
4. **muscle_group_volume_calculator** - 肌群训练量计算
5. **professional_program_designer** - 专业训练计划设计

### P1建议工具（8个）

6. **exercise_alternative_finder** - 动作替代查找
7. **movement_pattern_balancer** - 动作模式平衡
8. **intelligent_weight_calculator** - 智能负重计算
9. **safe_exercise_modifier** - 安全动作修改
10. **nutrition_intake_analyzer** - 营养摄入分析
11. **meal_plan_designer** - 膳食计划设计
12. **exercise_nutrition_optimization** - 运动营养优化
13. **tdee_calculator** - TDEE计算

### P2扩展工具（2个）

14. **periodized_program_designer** - 周期化训练设计
15. **training_split_designer** - 训练分化设计

---

## 相关文档

- **MCP工具架构**: [05-MCP工具架构.md](../../02-核心架构/03-编排层/03-MCP工具架构.md)
- **DAG编排器**: [09-步骤7-DAG编排器.md](./08-步骤7-DAG编排器.md)

---

**维护者**: 薛小川  
**最后更新**: 2025-12-17
