"""
DAML-RAG v2 MCP Server

基于 mcp 库的 MCP 协议服务器。
暴露浪潮引擎的检索能力给 YuzhenFork Agent。

启动方式:
  python -m src_v2.server  (stdio 模式)
  python -m src_v2.server --sse  (SSE 模式，端口 8002)
"""

import logging
import sys
import os
from typing import Any, Dict, Optional

# 确保路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

logger = logging.getLogger(__name__)

# 全局引擎实例（延迟初始化）
_wave_engine = None
_safety_engine = None


def _get_engines():
    """延迟初始化引擎"""
    global _wave_engine, _safety_engine

    if _wave_engine is not None:
        return _wave_engine, _safety_engine

    import asyncio
    from .config import get_config, EngineConfig
    from .engine.wave_engine import WaveEngine
    from .data.loader import DataStore
    from .rules.safety_engine import SafetyEngine

    logger.info("初始化浪潮引擎...")

    cfg = get_config()

    # 加载数据
    data = DataStore(config=cfg.data)
    # DataStore.load() 是 async，这里同步调用
    loop = asyncio.get_event_loop()
    if loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as pool:
            pool.submit(asyncio.run, data.load()).result()
    else:
        asyncio.run(data.load())

    # 创建引擎
    _wave_engine = WaveEngine(data_store=data, config=cfg.engine)

    # 创建安全引擎
    _safety_engine = SafetyEngine(
        graph_store=data.graph,
        metadata_store=data.metadata,
    )

    logger.info("浪潮引擎初始化完成")

    # 预热 Embedding 模型
    from .tools.embedding import warmup
    warmup()

    return _wave_engine, _safety_engine


# === MCP Server ===

server = Server("daml-rag-v2")


@server.list_tools()
async def list_tools():
    """列出所有可用工具"""
    return [
        Tool(
            name="search_exercises",
            description="搜索健身动作。基于浪潮引擎的智能检索，支持语义搜索+图谱推理+安全过滤。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "用户查询文本（自然语言），如'练胸的动作'、'腰突患者适合的背部训练'",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "用户ID（用于加载用户档案）",
                    },
                    "filters": {
                        "type": "object",
                        "description": "过滤条件",
                        "properties": {
                            "muscle_group": {"type": "string", "description": "目标肌群"},
                            "equipment": {"type": "string", "description": "器械类型"},
                            "difficulty": {"type": "string", "description": "难度等级"},
                            "body_part": {"type": "string", "description": "身体部位"},
                        },
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回数量，默认10",
                        "default": 10,
                    },
                },
                "required": ["query_text"],
            },
        ),
        Tool(
            name="get_exercise_detail",
            description="获取动作详细信息，包括目标肌群、动作要领、注意事项、禁忌症等。",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercise_id": {
                        "type": "string",
                        "description": "动作ID",
                    },
                },
                "required": ["exercise_id"],
            },
        ),
        Tool(
            name="graph_query",
            description="知识图谱查询。查询动作之间的关系、肌群关联、替代动作等。",
            inputSchema={
                "type": "object",
                "properties": {
                    "node_id": {
                        "type": "string",
                        "description": "起始节点ID（动作ID或肌群ID）",
                    },
                    "relation_type": {
                        "type": "string",
                        "description": "关系类型",
                        "enum": [
                            "TARGETS_PRIMARY",
                            "TARGETS_SECONDARY",
                            "REQUIRES_EQUIPMENT",
                            "ALTERNATIVE_TO",
                            "PROGRESSION_OF",
                            "CONTRAINDICATED_FOR",
                            "SYNERGIST_WITH",
                        ],
                    },
                    "depth": {
                        "type": "integer",
                        "description": "查询深度，默认1",
                        "default": 1,
                    },
                },
                "required": ["node_id"],
            },
        ),
        Tool(
            name="find_alternatives",
            description="查找替代动作。给定一个动作，找到功能相似但不同的替代选择。",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercise_id": {
                        "type": "string",
                        "description": "原动作ID",
                    },
                    "reason": {
                        "type": "string",
                        "description": "替代原因（如'没有器械'、'有伤病'）",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "用户ID（用于安全过滤）",
                    },
                },
                "required": ["exercise_id"],
            },
        ),
        Tool(
            name="check_exercise_safety",
            description="检查动作对特定用户的安全性。返回禁忌、警告和建议。",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercise_id": {
                        "type": "string",
                        "description": "动作ID",
                    },
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                    },
                    "injuries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "伤病列表（如果不传user_id，可直接传伤病）",
                    },
                },
                "required": ["exercise_id"],
            },
        ),
        # === 知识检索工具 ===
        Tool(
            name="search_knowledge",
            description="搜索训练知识库。查找训练原则、方法论、恢复策略等专业知识。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "查询文本（如'渐进超负荷原则'、'如何安排deload周'）",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回数量，默认5",
                        "default": 5,
                    },
                },
                "required": ["query_text"],
            },
        ),
        Tool(
            name="search_foods",
            description="搜索食物营养数据。查找高蛋白食物、特定营养素食物等。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_text": {
                        "type": "string",
                        "description": "查询文本（如'高蛋白食物'、'鸡胸肉'、'低GI碳水'）",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "返回数量，默认10",
                        "default": 10,
                    },
                },
                "required": ["query_text"],
            },
        ),
        Tool(
            name="get_food_detail",
            description="获取食物详细营养信息，包括完整营养成分。",
            inputSchema={
                "type": "object",
                "properties": {
                    "food_id": {
                        "type": "string",
                        "description": "食物ID",
                    },
                },
                "required": ["food_id"],
            },
        ),
        Tool(
            name="get_strength_standards",
            description="查询力量标准。根据动作、性别、体重查询各水平的力量标准。",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercise_name": {
                        "type": "string",
                        "description": "动作名称（如'卧推'、'深蹲'）",
                    },
                    "level": {
                        "type": "string",
                        "description": "训练水平",
                        "enum": ["beginner", "novice", "intermediate", "advanced", "elite"],
                    },
                    "gender": {
                        "type": "string",
                        "description": "性别",
                        "enum": ["male", "female"],
                    },
                    "body_weight": {
                        "type": "number",
                        "description": "体重(kg)",
                    },
                },
            },
        ),
        # === 计算规划工具 ===
        Tool(
            name="calculate_tdee",
            description="计算每日总能量消耗(TDEE)和宏量营养素分配。基于Mifflin-St Jeor公式。",
            inputSchema={
                "type": "object",
                "properties": {
                    "gender": {"type": "string", "enum": ["male", "female"]},
                    "age": {"type": "integer", "description": "年龄"},
                    "weight_kg": {"type": "number", "description": "体重(kg)"},
                    "height_cm": {"type": "number", "description": "身高(cm)"},
                    "activity_level": {
                        "type": "string",
                        "description": "活动水平",
                        "enum": ["sedentary", "light", "moderate", "active", "very_active"],
                    },
                    "goal": {
                        "type": "string",
                        "description": "目标",
                        "enum": ["lose_fat", "maintain", "lean_bulk", "bulk"],
                    },
                },
                "required": ["gender", "age", "weight_kg", "height_cm"],
            },
        ),
        Tool(
            name="calculate_training_volume",
            description="计算肌群训练容量(MEV/MAV/MRV)。基于RP训练容量理论。",
            inputSchema={
                "type": "object",
                "properties": {
                    "muscle_group": {
                        "type": "string",
                        "description": "肌群名称（中英文均可，如'胸'、'chest'、'背部'）",
                    },
                    "training_level": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["hypertrophy", "strength", "endurance"],
                    },
                    "recovery_capacity": {
                        "type": "string",
                        "enum": ["low", "normal", "high"],
                    },
                },
                "required": ["muscle_group"],
            },
        ),
        Tool(
            name="calculate_1rm",
            description="估算1RM（单次最大重复重量）。基于Epley公式。",
            inputSchema={
                "type": "object",
                "properties": {
                    "weight": {"type": "number", "description": "使用重量(kg)"},
                    "reps": {"type": "integer", "description": "完成次数"},
                },
                "required": ["weight", "reps"],
            },
        ),
        Tool(
            name="assess_strength_level",
            description="评估力量水平。根据体重和举起重量判断训练水平。",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercise": {
                        "type": "string",
                        "description": "动作名称（bench_press/squat/deadlift/overhead_press）",
                    },
                    "one_rm": {"type": "number", "description": "1RM重量(kg)"},
                    "body_weight": {"type": "number", "description": "体重(kg)"},
                    "gender": {"type": "string", "enum": ["male", "female"]},
                },
                "required": ["exercise", "one_rm", "body_weight"],
            },
        ),
        Tool(
            name="design_training_split",
            description="设计训练分化方案。根据训练频率和目标推荐分化方式。",
            inputSchema={
                "type": "object",
                "properties": {
                    "days_per_week": {
                        "type": "integer",
                        "description": "每周训练天数(2-6)",
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["hypertrophy", "strength", "general_fitness"],
                    },
                    "training_level": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                    },
                    "weak_points": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "弱项肌群列表",
                    },
                },
                "required": ["days_per_week"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]):
    """执行工具调用"""
    try:
        wave_engine, safety_engine = _get_engines()

        if name == "search_exercises":
            return await _handle_search_exercises(arguments, wave_engine, safety_engine)
        elif name == "get_exercise_detail":
            return await _handle_get_exercise_detail(arguments, wave_engine)
        elif name == "graph_query":
            return await _handle_graph_query(arguments, wave_engine)
        elif name == "find_alternatives":
            return await _handle_find_alternatives(arguments, wave_engine, safety_engine)
        elif name == "check_exercise_safety":
            return await _handle_check_safety(arguments, safety_engine)
        elif name == "search_knowledge":
            return await _handle_search_knowledge(arguments, wave_engine)
        elif name == "search_foods":
            return await _handle_search_foods(arguments, wave_engine)
        elif name == "get_food_detail":
            return _handle_get_food_detail(arguments, wave_engine)
        elif name == "get_strength_standards":
            return _handle_get_strength_standards(arguments, wave_engine)
        elif name == "calculate_tdee":
            return _handle_calculate_tdee(arguments)
        elif name == "calculate_training_volume":
            return _handle_calculate_training_volume(arguments)
        elif name == "calculate_1rm":
            return _handle_calculate_1rm(arguments)
        elif name == "assess_strength_level":
            return _handle_assess_strength_level(arguments)
        elif name == "design_training_split":
            return _handle_design_training_split(arguments)
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]

    except Exception as e:
        logger.exception(f"工具执行失败: {name}")
        import json as _json
        error_payload = _json.dumps({"error": str(e)}, ensure_ascii=False)
        return [TextContent(type="text", text=error_payload)]


# === 工具处理函数 ===

async def _handle_search_exercises(args: Dict, wave_engine, safety_engine):
    """处理 search_exercises"""
    import json
    from .tools.search_exercises import search_exercises

    query_text = args["query_text"]
    filters = args.get("filters")
    top_k = args.get("top_k", 10)

    # TODO: 从 user_id 加载用户档案
    user_profile = None
    user_id = args.get("user_id")
    if user_id:
        user_profile = _load_user_profile(user_id)

    result = await search_exercises(
        query_text=query_text,
        user_profile=user_profile,
        filters=filters,
        top_k=top_k,
        wave_engine=wave_engine,
        safety_engine=safety_engine,
    )

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_get_exercise_detail(args: Dict, wave_engine):
    """处理 get_exercise_detail"""
    import json

    exercise_id = args["exercise_id"]
    meta = None
    if wave_engine.data.metadata:
        meta = wave_engine.data.metadata.get_exercise(exercise_id)

    if not meta:
        return [TextContent(type="text", text=f"未找到动作: {exercise_id}")]

    # 补充图谱关系
    if wave_engine.data.graph and wave_engine.data.graph.ready:
        relations = wave_engine.data.graph.get_all_relations(exercise_id)
        meta["relations"] = {
            rel_type: [e.get("target", "") for e in edges]
            for rel_type, edges in relations.items()
        }

    return [TextContent(type="text", text=json.dumps(meta, ensure_ascii=False, indent=2))]


async def _handle_graph_query(args: Dict, wave_engine):
    """处理 graph_query"""
    import json

    node_id = args["node_id"]
    relation_type = args.get("relation_type")
    depth = args.get("depth", 1)

    if not wave_engine.data.graph or not wave_engine.data.graph.ready:
        return [TextContent(type="text", text="图谱未加载")]

    if relation_type:
        edges = wave_engine.data.graph.get_relations(node_id, relation_type)
        result = {
            "node_id": node_id,
            "relation_type": relation_type,
            "targets": [e.get("target", "") for e in edges],
            "count": len(edges),
        }
    else:
        all_rels = wave_engine.data.graph.get_all_relations(node_id)
        result = {
            "node_id": node_id,
            "relations": {
                rel_type: [e.get("target", "") for e in edges]
                for rel_type, edges in all_rels.items()
            },
        }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_find_alternatives(args: Dict, wave_engine, safety_engine):
    """处理 find_alternatives"""
    import json
    from .tools.search_exercises import search_exercises

    exercise_id = args["exercise_id"]
    reason = args.get("reason", "")

    # 获取原动作的向量
    meta = None
    if wave_engine.data.metadata:
        meta = wave_engine.data.metadata.get_exercise(exercise_id)

    # 用原动作名称 + 替代原因作为查询
    exercise_name = meta.get("name_zh", exercise_id) if meta else exercise_id
    query = f"{exercise_name}的替代动作 {reason}".strip()

    # 加载用户档案
    user_profile = None
    user_id = args.get("user_id")
    if user_id:
        user_profile = _load_user_profile(user_id)

    result = await search_exercises(
        query_text=query,
        user_profile=user_profile,
        top_k=5,
        wave_engine=wave_engine,
        safety_engine=safety_engine,
    )

    # 排除原动作
    result["exercises"] = [e for e in result["exercises"] if e["id"] != exercise_id]

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_check_safety(args: Dict, safety_engine):
    """处理 check_exercise_safety"""
    import json

    exercise_id = args["exercise_id"]
    injuries = args.get("injuries", [])
    user_id = args.get("user_id")

    user_profile = {}
    if user_id:
        user_profile = _load_user_profile(user_id) or {}

    if injuries:
        user_profile["injuries"] = [{"type": inj} for inj in injuries]

    if not safety_engine:
        return [TextContent(type="text", text="安全引擎未初始化")]

    report = safety_engine.check([exercise_id], user_profile)

    result = {
        "exercise_id": exercise_id,
        "safe": exercise_id not in report.blocked_ids,
        "blocked": exercise_id in report.blocked_ids,
        "warnings": [
            {"rule": w.rule_name, "message": w.reason}
            for w in report.warnings
            if w.item_id == exercise_id
        ],
        "penalties": report.penalties.get(exercise_id, 0.0),
    }

    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# === 新工具处理函数 ===

async def _handle_search_knowledge(args: Dict, wave_engine):
    """处理 search_knowledge"""
    import json
    from .tools.knowledge_and_food import search_knowledge

    result = await search_knowledge(
        query_text=args["query_text"],
        top_k=args.get("top_k", 5),
        wave_engine=wave_engine,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_search_foods(args: Dict, wave_engine):
    """处理 search_foods"""
    import json
    from .tools.knowledge_and_food import search_foods

    result = await search_foods(
        query_text=args["query_text"],
        top_k=args.get("top_k", 10),
        wave_engine=wave_engine,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_get_food_detail(args: Dict, wave_engine):
    """处理 get_food_detail"""
    import json
    from .tools.knowledge_and_food import get_food_detail

    result = get_food_detail(
        food_id=args["food_id"],
        data_store=wave_engine.data,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_get_strength_standards(args: Dict, wave_engine):
    """处理 get_strength_standards"""
    import json
    from .tools.knowledge_and_food import get_strength_standards

    result = get_strength_standards(
        exercise_name=args.get("exercise_name"),
        level=args.get("level"),
        gender=args.get("gender"),
        body_weight=args.get("body_weight"),
        data_store=wave_engine.data,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_calculate_tdee(args: Dict):
    """处理 calculate_tdee"""
    import json
    from .tools.calculators import calculate_tdee

    result = calculate_tdee(
        gender=args["gender"],
        age=args["age"],
        weight_kg=args["weight_kg"],
        height_cm=args["height_cm"],
        activity_level=args.get("activity_level", "moderate"),
        goal=args.get("goal", "maintain"),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_calculate_training_volume(args: Dict):
    """处理 calculate_training_volume"""
    import json
    from .tools.calculators import calculate_training_volume

    result = calculate_training_volume(
        muscle_group=args["muscle_group"],
        training_level=args.get("training_level", "intermediate"),
        goal=args.get("goal", "hypertrophy"),
        recovery_capacity=args.get("recovery_capacity", "normal"),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_calculate_1rm(args: Dict):
    """处理 calculate_1rm"""
    import json
    from .tools.calculators import calculate_1rm

    result = calculate_1rm(
        weight=args["weight"],
        reps=args["reps"],
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_assess_strength_level(args: Dict):
    """处理 assess_strength_level"""
    import json
    from .tools.calculators import assess_strength_level

    result = assess_strength_level(
        exercise_name=args["exercise_name"],
        one_rm=args["one_rm"],
        body_weight=args["body_weight"],
        gender=args.get("gender", "male"),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_design_training_split(args: Dict):
    """处理 design_training_split"""
    import json
    from .tools.calculators import design_training_split

    result = design_training_split(
        days_per_week=args["days_per_week"],
        goal=args.get("goal", "hypertrophy"),
        training_level=args.get("training_level", "intermediate"),
        weak_points=args.get("weak_points"),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]
    """加载用户档案

    TODO: 从 Redis/MySQL 加载真实用户档案
    """
    # 暂时返回空档案
    return {"user_id": user_id, "fitness_level": "intermediate"}


# === 入口 ===

async def main():
    """MCP 服务器主入口"""
    logging.basicConfig(level=logging.INFO)
    logger.info("DAML-RAG v2 MCP Server 启动 (stdio 模式)")

    # 预热引擎
    _get_engines()

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
