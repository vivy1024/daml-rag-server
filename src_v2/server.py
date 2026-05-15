"""
DAML-RAG v2 MCP Server

基于 mcp 库的 MCP 协议服务器。
暴露浪潮引擎的检索能力给 YuzhenFork Agent。

启动方式:
  python -m src_v2.server  (stdio 模式)
  python -m src_v2.server --sse  (SSE 模式，端口 8002)
"""

import logging
import json
import sys
import os
from typing import Any, Dict, List, Optional

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
        # === 图谱专项查询工具（新增） ===
        Tool(
            name="get_contraindications",
            description="查询伤病禁忌动作。给定伤病列表，返回所有禁忌动作+风险等级+替代方案。基于6371条禁忌关系。",
            inputSchema={
                "type": "object",
                "properties": {
                    "injuries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "伤病列表，如['腰椎间盘突出', '肩袖损伤']",
                    },
                },
                "required": ["injuries"],
            },
        ),
        Tool(
            name="get_posture_corrections",
            description="查询体态矫正方案。给定体态问题，返回矫正动作+应避免动作+紧张/薄弱肌群分析。",
            inputSchema={
                "type": "object",
                "properties": {
                    "issue": {
                        "type": "string",
                        "description": "体态问题，如'圆肩'、'骨盆前倾'、'驼背'",
                    },
                },
                "required": ["issue"],
            },
        ),
        Tool(
            name="get_rehabilitation_protocol",
            description="查询康复训练协议。给定伤病类型，返回禁忌动作+安全动作+康复阶段。",
            inputSchema={
                "type": "object",
                "properties": {
                    "injury": {
                        "type": "string",
                        "description": "伤病类型，如'肩袖损伤'、'ACL重建术后'",
                    },
                    "phase": {
                        "type": "string",
                        "description": "康复阶段（early/mid/late），可选",
                        "enum": ["early", "mid", "late"],
                    },
                },
                "required": ["injury"],
            },
        ),
        Tool(
            name="get_muscle_exercise_map",
            description="查询肌群对应的所有训练动作。支持按难度和器械过滤。",
            inputSchema={
                "type": "object",
                "properties": {
                    "muscle": {
                        "type": "string",
                        "description": "肌群名称，如'胸肌'、'肱二头肌'、'臀部'",
                    },
                    "level": {
                        "type": "string",
                        "description": "难度过滤",
                        "enum": ["初级", "中级", "高级"],
                    },
                    "equipment": {
                        "type": "string",
                        "description": "器械过滤，如'哑铃'、'杠铃'、'徒手'",
                    },
                },
                "required": ["muscle"],
            },
        ),
        # === 用户数据工具（新增） ===
        Tool(
            name="get_user_profile",
            description="获取用户完整健身档案（身高/体重/目标/伤病/训练水平/力量数据）。需要user_id。",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="get_training_history",
            description="获取用户训练记录。返回最近N天的训练数据（动作/重量/次数/RPE）和力量趋势。",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                    },
                    "days": {
                        "type": "integer",
                        "description": "最近N天，默认30",
                        "default": 30,
                    },
                    "exercise_name": {
                        "type": "string",
                        "description": "按动作名称过滤（可选）",
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="get_progress_data",
            description="获取用户进度数据（体重/体脂/FFMI/力量趋势）。返回时间序列和趋势分析。",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                    },
                    "metric": {
                        "type": "string",
                        "description": "指标类型",
                        "enum": ["weight", "body_fat", "ffmi", "strength"],
                    },
                    "days": {
                        "type": "integer",
                        "description": "最近N天，默认90",
                        "default": 90,
                    },
                },
                "required": ["user_id"],
            },
        ),
        Tool(
            name="save_training_plan",
            description="将AI生成的训练计划保存到用户账户。",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "string",
                        "description": "用户ID",
                    },
                    "plan": {
                        "type": "object",
                        "description": "训练计划数据（含名称、目标、动作列表等）",
                    },
                },
                "required": ["user_id", "plan"],
            },
        ),
        # === 智能推理工具（新增） ===
        Tool(
            name="generate_training_cycle",
            description="生成完整训练周期方案。结合用户水平、目标、器械、伤病，输出可直接执行的训练计划（含动作/组数/次数/强度/渐进策略/deload）。",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_profile": {
                        "type": "object",
                        "description": "用户档案（含 training.level, health.injuries, goals 等）",
                    },
                    "goal": {
                        "type": "string",
                        "enum": ["hypertrophy", "strength", "general_fitness"],
                    },
                    "days_per_week": {
                        "type": "integer",
                        "description": "每星期训练天数(2-6)",
                    },
                    "available_equipment": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "可用器械列表",
                    },
                    "cycle_weeks": {
                        "type": "integer",
                        "description": "周期长度（几个训练周期为一轮），默认4",
                        "default": 4,
                    },
                },
                "required": ["user_profile", "days_per_week"],
            },
        ),
        Tool(
            name="analyze_training_balance",
            description="分析训练平衡性。对比各肌群实际训练量与推荐标准(MEV/MAV/MRV)，识别失衡和弱项。",
            inputSchema={
                "type": "object",
                "properties": {
                    "training_records": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "exercise": {"type": "string"},
                                "muscle_group": {"type": "string"},
                                "sets": {"type": "integer"},
                                "date": {"type": "string"},
                            },
                        },
                        "description": "训练记录列表",
                    },
                },
                "required": ["training_records"],
            },
        ),
        Tool(
            name="calculate_progressive_overload",
            description="计算渐进超负荷建议。基于最近训练记录分析趋势，给出下次训练的重量/次数建议和是否需要deload。",
            inputSchema={
                "type": "object",
                "properties": {
                    "exercise_name": {
                        "type": "string",
                        "description": "动作名称",
                    },
                    "recent_records": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "weight": {"type": "number"},
                                "reps": {"type": "integer"},
                                "date": {"type": "string"},
                            },
                        },
                        "description": "最近几次训练记录（按时间顺序）",
                    },
                },
                "required": ["exercise_name", "recent_records"],
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
        # === 图谱专项工具 ===
        elif name == "get_contraindications":
            return _handle_get_contraindications(arguments, wave_engine)
        elif name == "get_posture_corrections":
            return _handle_get_posture_corrections(arguments, wave_engine)
        elif name == "get_rehabilitation_protocol":
            return _handle_get_rehabilitation_protocol(arguments, wave_engine)
        elif name == "get_muscle_exercise_map":
            return _handle_get_muscle_exercise_map(arguments, wave_engine)
        # === 用户数据工具 ===
        elif name == "get_user_profile":
            return await _handle_get_user_profile(arguments)
        elif name == "get_training_history":
            return await _handle_get_training_history(arguments)
        elif name == "get_progress_data":
            return await _handle_get_progress_data(arguments)
        elif name == "save_training_plan":
            return await _handle_save_training_plan(arguments)
        # === 智能推理工具 ===
        elif name == "generate_training_cycle":
            return _handle_generate_training_cycle(arguments, wave_engine)
        elif name == "analyze_training_balance":
            return _handle_analyze_training_balance(arguments)
        elif name == "calculate_progressive_overload":
            return _handle_calculate_progressive_overload(arguments)
        else:
            return [TextContent(type="text", text=f"未知工具: {name}")]

    except Exception as e:
        logger.exception(f"工具执行失败: {name}")
        error_payload = json.dumps({"error": str(e)}, ensure_ascii=False)
        return [TextContent(type="text", text=error_payload)]


# === 工具处理函数 ===

async def _handle_search_exercises(args: Dict, wave_engine, safety_engine):
    """处理 search_exercises"""

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

    from .tools.knowledge_and_food import search_knowledge

    result = await search_knowledge(
        query_text=args["query_text"],
        top_k=args.get("top_k", 5),
        wave_engine=wave_engine,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_search_foods(args: Dict, wave_engine):
    """处理 search_foods"""

    from .tools.knowledge_and_food import search_foods

    result = await search_foods(
        query_text=args["query_text"],
        top_k=args.get("top_k", 10),
        wave_engine=wave_engine,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_get_food_detail(args: Dict, wave_engine):
    """处理 get_food_detail"""

    from .tools.knowledge_and_food import get_food_detail

    result = get_food_detail(
        food_id=args["food_id"],
        data_store=wave_engine.data,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_get_strength_standards(args: Dict, wave_engine):
    """处理 get_strength_standards"""

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

    from .tools.calculators import calculate_1rm

    result = calculate_1rm(
        weight=args["weight"],
        reps=args["reps"],
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_assess_strength_level(args: Dict):
    """处理 assess_strength_level"""

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

    from .tools.calculators import design_training_split

    result = design_training_split(
        days_per_week=args["days_per_week"],
        goal=args.get("goal", "hypertrophy"),
        training_level=args.get("training_level", "intermediate"),
        weak_points=args.get("weak_points"),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _load_user_profile(user_id: str) -> Optional[Dict]:
    """加载用户档案（同步版，用于旧工具兼容）

    新工具应使用 async 的 user_data.get_user_profile()
    """
    # 暂时返回基础档案，后续接通 BackendClient
    return {"user_id": user_id, "fitness_level": "intermediate"}


# === 图谱专项工具处理函数 ===

def _handle_get_contraindications(args: Dict, wave_engine):
    """处理 get_contraindications"""

    from .tools.graph_queries import get_contraindications

    result = get_contraindications(
        injuries=args["injuries"],
        graph=wave_engine.data.graph,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_get_posture_corrections(args: Dict, wave_engine):
    """处理 get_posture_corrections"""

    from .tools.graph_queries import get_posture_corrections

    result = get_posture_corrections(
        issue=args["issue"],
        graph=wave_engine.data.graph,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_get_rehabilitation_protocol(args: Dict, wave_engine):
    """处理 get_rehabilitation_protocol"""

    from .tools.graph_queries import get_rehabilitation_protocol

    result = get_rehabilitation_protocol(
        injury=args["injury"],
        phase=args.get("phase"),
        graph=wave_engine.data.graph,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_get_muscle_exercise_map(args: Dict, wave_engine):
    """处理 get_muscle_exercise_map"""

    from .tools.graph_queries import get_muscle_exercise_map

    result = get_muscle_exercise_map(
        muscle=args["muscle"],
        graph=wave_engine.data.graph,
        level=args.get("level"),
        equipment=args.get("equipment"),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# === 用户数据工具处理函数 ===

async def _handle_get_user_profile(args: Dict):
    """处理 get_user_profile"""

    from .tools.user_data import get_user_profile

    result = await get_user_profile(user_id=args["user_id"])
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_get_training_history(args: Dict):
    """处理 get_training_history"""

    from .tools.user_data import get_training_history

    result = await get_training_history(
        user_id=args["user_id"],
        days=args.get("days", 30),
        exercise_name=args.get("exercise_name"),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_get_progress_data(args: Dict):
    """处理 get_progress_data"""

    from .tools.user_data import get_progress_data

    result = await get_progress_data(
        user_id=args["user_id"],
        metric=args.get("metric", "weight"),
        days=args.get("days", 90),
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def _handle_save_training_plan(args: Dict):
    """处理 save_training_plan"""

    from .tools.user_data import save_training_plan

    result = await save_training_plan(
        user_id=args["user_id"],
        plan_data=args["plan"],
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# === 智能推理工具处理函数 ===

def _handle_generate_training_cycle(args: Dict, wave_engine):
    """处理 generate_training_cycle"""
    from .tools.smart_planning import generate_training_cycle

    result = generate_training_cycle(
        user_profile=args["user_profile"],
        goal=args.get("goal", "hypertrophy"),
        days_per_week=args["days_per_week"],
        available_equipment=args.get("available_equipment"),
        cycle_weeks=args.get("cycle_weeks", 4),
        graph=wave_engine.data.graph if wave_engine else None,
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_analyze_training_balance(args: Dict):
    """处理 analyze_training_balance"""
    from .tools.smart_planning import analyze_training_balance

    result = analyze_training_balance(
        training_records=args["training_records"],
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


def _handle_calculate_progressive_overload(args: Dict):
    """处理 calculate_progressive_overload"""
    from .tools.smart_planning import calculate_progressive_overload

    result = calculate_progressive_overload(
        exercise_name=args["exercise_name"],
        recent_records=args["recent_records"],
    )
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


# === 入口 ===

async def main():
    """MCP 服务器主入口"""
    logging.basicConfig(level=logging.INFO)

    # 预热引擎
    _get_engines()

    if "--sse" in sys.argv:
        # SSE 模式（HTTP，供 YuzhenFork 等外部客户端连接）
        from mcp.server.sse import SseServerTransport
        from starlette.applications import Starlette
        from starlette.routing import Route
        import uvicorn

        sse = SseServerTransport("/messages")

        async def handle_sse(request):
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                await server.run(streams[0], streams[1], server.create_initialization_options())

        async def handle_messages(request):
            await sse.handle_post_message(request.scope, request.receive, request._send)

        app = Starlette(routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ])

        port = int(os.environ.get("MCP_SSE_PORT", "8002"))
        logger.info(f"DAML-RAG v2 MCP Server 启动 (SSE 模式, 端口 {port})")
        uvicorn.run(app, host="0.0.0.0", port=port)
    else:
        # stdio 模式（默认）
        logger.info("DAML-RAG v2 MCP Server 启动 (stdio 模式)")
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
