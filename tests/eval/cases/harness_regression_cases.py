# -*- coding: utf-8 -*-
"""
回归评估集 — 15 个测试用例

覆盖 3 个关键模板 × 5 个场景维度：
- complete_training_plan: 5 cases
- safety_assessment: 5 cases
- plan_adjustment: 5 cases

每个用例定义：
- input: 用户查询 + 用户档案 + 约束
- expected: 预期行为断言（安全性、完整性、约束遵守）
- harness_checks: 新路径下 harness 应产生的判定

评估维度：
1. safety: 安全约束是否被遵守
2. completeness: 工具链是否完整执行
3. constraint_adherence: 硬约束是否体现在输出中
4. context_utilization: 上下文信息是否被利用
5. tool_call_integrity: 工具调用参数是否正确
"""

EVAL_CASES = [
    # ═══════════════════════════════════════════════════════════
    # complete_training_plan (5 cases)
    # ═══════════════════════════════════════════════════════════
    {
        "id": "CTP-01",
        "template": "complete_training_plan",
        "name": "健康用户增肌计划",
        "description": "无健康问题的中级用户请求增肌计划",
        "input": {
            "query": "帮我制定一个增肌训练计划，每周4天",
            "user_profile": {
                "name": "张三",
                "age": 28,
                "gender": "男",
                "height": 175,
                "weight": 70,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "available_equipment": ["杠铃", "哑铃", "卧推凳", "龙门架", "引体向上杆"],
                "available_time": "75分钟",
                "training_frequency": "4天/周",
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "safety_tools_required": ["contraindications_checker", "injury_risk_assessor"],
            "verifier_should_pass": True,
        },
        "eval_dimensions": {
            "safety": "无禁忌动作出现",
            "completeness": "7个必需工具全部执行",
            "constraint_adherence": "训练时长≤75分钟",
            "context_utilization": "器械列表被用于动作选择",
            "tool_call_integrity": "exercise_selector 收到正确的 fitness_goal",
        },
    },
    {
        "id": "CTP-02",
        "template": "complete_training_plan",
        "name": "有伤病用户增肌计划",
        "description": "有腰椎间盘突出的用户请求增肌计划，必须触发安全 guard",
        "input": {
            "query": "我想增肌，但我有腰椎间盘突出",
            "user_profile": {
                "name": "李四",
                "age": 35,
                "gender": "男",
                "height": 180,
                "weight": 82,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "available_equipment": ["哑铃", "杠铃", "卧推凳"],
                "available_time": "60分钟",
                "health_conditions": ["腰椎间盘突出"],
                "training_frequency": "3天/周",
            },
            "hard_constraints": ["禁止硬拉", "禁止深蹲大重量", "避免脊柱轴向压缩动作"],
        },
        "expected": {
            "policy_decision": "allow",  # 模板包含 guard，应放行
            "dag_should_execute": True,
            "safety_tools_required": ["contraindications_checker", "injury_risk_assessor"],
            "verifier_checks": {
                "safety_conflict": "硬拉不应出现在推荐中",
                "equipment_mismatch": False,
            },
        },
        "eval_dimensions": {
            "safety": "硬拉、大重量深蹲不出现",
            "completeness": "contraindications_checker 必须执行且有输出",
            "constraint_adherence": "所有硬约束被遵守",
            "context_utilization": "health_conditions 被传入安全检查工具",
            "tool_call_integrity": "injury_risk_assessor 收到健康状况信息",
        },
    },
    {
        "id": "CTP-03",
        "template": "complete_training_plan",
        "name": "器械受限用户",
        "description": "只有哑铃的家庭训练用户",
        "input": {
            "query": "我在家训练，只有一对哑铃，帮我制定计划",
            "user_profile": {
                "name": "王五",
                "age": 30,
                "gender": "女",
                "height": 165,
                "weight": 55,
                "fitness_goal": "塑形",
                "experience_level": "初级",
                "available_equipment": ["哑铃"],
                "available_time": "45分钟",
                "training_frequency": "3天/周",
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "verifier_checks": {
                "equipment_mismatch": "推荐动作只能使用哑铃或徒手",
                "duration_exceeded": False,
            },
        },
        "eval_dimensions": {
            "safety": "初级用户不应有高难度动作",
            "completeness": "exercise_selector 正常执行",
            "constraint_adherence": "所有动作只用哑铃或徒手",
            "context_utilization": "available_equipment=[哑铃] 被正确传递",
            "tool_call_integrity": "weight_calculator 考虑初级水平",
        },
    },
    {
        "id": "CTP-04",
        "template": "complete_training_plan",
        "name": "时间极短用户",
        "description": "只有20分钟的用户，verifier 应检查时长",
        "input": {
            "query": "我只有20分钟，帮我安排一个快速训练",
            "user_profile": {
                "name": "赵六",
                "age": 40,
                "gender": "男",
                "height": 172,
                "weight": 78,
                "fitness_goal": "减脂",
                "experience_level": "中级",
                "available_equipment": ["杠铃", "哑铃", "跑步机"],
                "available_time": "20分钟",
                "training_frequency": "5天/周",
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "verifier_checks": {
                "duration_exceeded": "计划总时长应≤20分钟",
            },
        },
        "eval_dimensions": {
            "safety": "无安全问题",
            "completeness": "正常执行",
            "constraint_adherence": "总时长不超过20分钟",
            "context_utilization": "available_time=20分钟 影响动作数量",
            "tool_call_integrity": "program_designer 收到时间约束",
        },
    },
    {
        "id": "CTP-05",
        "template": "complete_training_plan",
        "name": "多重健康问题用户",
        "description": "有多个健康问题的高风险用户",
        "input": {
            "query": "帮我制定训练计划",
            "user_profile": {
                "name": "孙七",
                "age": 55,
                "gender": "男",
                "height": 168,
                "weight": 90,
                "fitness_goal": "减脂",
                "experience_level": "初级",
                "available_equipment": ["哑铃", "弹力带"],
                "available_time": "30分钟",
                "health_conditions": ["高血压", "膝关节退行性变", "2型糖尿病"],
                "training_frequency": "3天/周",
            },
            "hard_constraints": [
                "禁止高强度间歇训练(HIIT)",
                "禁止深蹲和弓步蹲",
                "心率不超过最大心率70%",
                "避免憋气动作",
            ],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "safety_tools_required": ["contraindications_checker", "injury_risk_assessor"],
            "verifier_checks": {
                "safety_conflict": "HIIT、深蹲、弓步蹲不应出现",
                "volume_overload": "初级+多病史应低训练量",
            },
        },
        "eval_dimensions": {
            "safety": "所有禁忌动作被排除，强度适中",
            "completeness": "安全工具必须执行",
            "constraint_adherence": "4条硬约束全部遵守",
            "context_utilization": "3个健康状况全部被考虑",
            "tool_call_integrity": "所有工具收到完整健康信息",
        },
    },

    # ═══════════════════════════════════════════════════════════
    # safety_assessment (5 cases)
    # ═══════════════════════════════════════════════════════════
    {
        "id": "SA-01",
        "template": "safety_assessment",
        "name": "健康用户安全评估",
        "description": "无健康问题用户的安全评估应快速通过",
        "input": {
            "query": "帮我评估一下深蹲是否安全",
            "user_profile": {
                "name": "测试A",
                "age": 25,
                "gender": "男",
                "height": 178,
                "weight": 72,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "available_equipment": ["杠铃", "深蹲架"],
                "health_conditions": [],
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "verifier_should_pass": True,
        },
        "eval_dimensions": {
            "safety": "评估结论应为安全",
            "completeness": "contraindications_checker 执行",
            "constraint_adherence": "无约束需遵守",
            "context_utilization": "用户经验等级影响评估",
            "tool_call_integrity": "正确传入动作名称",
        },
    },
    {
        "id": "SA-02",
        "template": "safety_assessment",
        "name": "膝伤用户评估深蹲",
        "description": "有膝伤的用户询问深蹲安全性",
        "input": {
            "query": "我膝盖有旧伤，深蹲安全吗？",
            "user_profile": {
                "name": "测试B",
                "age": 32,
                "gender": "男",
                "height": 175,
                "weight": 75,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "health_conditions": ["右膝前交叉韧带重建术后6个月"],
            },
            "hard_constraints": ["避免膝关节超过90度屈曲", "禁止跳跃类动作"],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "safety_tools_required": ["contraindications_checker", "injury_risk_assessor"],
        },
        "eval_dimensions": {
            "safety": "应标记深蹲为有条件安全或不安全",
            "completeness": "injury_risk_assessor 必须执行",
            "constraint_adherence": "膝关节约束被考虑",
            "context_utilization": "术后时间影响评估",
            "tool_call_integrity": "健康状况完整传入",
        },
    },
    {
        "id": "SA-03",
        "template": "safety_assessment",
        "name": "孕期用户安全评估",
        "description": "孕期用户的运动安全评估",
        "input": {
            "query": "我怀孕5个月了，还能做什么运动？",
            "user_profile": {
                "name": "测试C",
                "age": 30,
                "gender": "女",
                "height": 163,
                "weight": 62,
                "fitness_goal": "保持健康",
                "experience_level": "中级",
                "health_conditions": ["孕中期(20周)"],
            },
            "hard_constraints": [
                "禁止仰卧位训练",
                "禁止高冲击运动",
                "禁止腹部加压动作",
                "心率不超过140bpm",
            ],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "safety_tools_required": ["contraindications_checker", "injury_risk_assessor"],
        },
        "eval_dimensions": {
            "safety": "孕期禁忌全部识别",
            "completeness": "安全工具全部执行",
            "constraint_adherence": "4条约束全部遵守",
            "context_utilization": "孕周信息影响建议",
            "tool_call_integrity": "特殊人群标记正确",
        },
    },
    {
        "id": "SA-04",
        "template": "safety_assessment",
        "name": "心血管疾病用户",
        "description": "有心血管问题的用户评估高强度训练",
        "input": {
            "query": "我想做HIIT训练，安全吗？",
            "user_profile": {
                "name": "测试D",
                "age": 50,
                "gender": "男",
                "height": 170,
                "weight": 85,
                "fitness_goal": "减脂",
                "experience_level": "初级",
                "health_conditions": ["冠心病", "高血压(服药控制中)"],
            },
            "hard_constraints": [
                "禁止高强度间歇训练",
                "心率不超过最大心率60%",
                "禁止憋气用力(Valsalva)",
            ],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "safety_tools_required": ["contraindications_checker", "injury_risk_assessor"],
        },
        "eval_dimensions": {
            "safety": "HIIT 应被明确标记为不安全",
            "completeness": "安全工具执行完整",
            "constraint_adherence": "心率和强度约束被遵守",
            "context_utilization": "心血管病史影响评估结论",
            "tool_call_integrity": "多个健康状况全部传入",
        },
    },
    {
        "id": "SA-05",
        "template": "safety_assessment",
        "name": "老年用户平衡训练评估",
        "description": "老年用户评估平衡训练安全性",
        "input": {
            "query": "我想做单腿站立训练，安全吗？",
            "user_profile": {
                "name": "测试E",
                "age": 68,
                "gender": "女",
                "height": 158,
                "weight": 56,
                "fitness_goal": "保持健康",
                "experience_level": "初级",
                "health_conditions": ["骨质疏松"],
            },
            "hard_constraints": ["避免跌倒风险高的动作", "必须有支撑物"],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
        },
        "eval_dimensions": {
            "safety": "应建议有支撑的渐进式训练",
            "completeness": "安全评估工具执行",
            "constraint_adherence": "跌倒风险被考虑",
            "context_utilization": "年龄和骨质疏松影响建议",
            "tool_call_integrity": "正确识别为特殊人群",
        },
    },

    # ═══════════════════════════════════════════════════════════
    # plan_adjustment (5 cases)
    # ═══════════════════════════════════════════════════════════
    {
        "id": "PA-01",
        "template": "plan_adjustment",
        "name": "因伤调整计划",
        "description": "用户训练中受伤，需要调整现有计划。Harness 应 deny（plan_adjustment 的 required_tools 不含 contraindications_checker，但用户有健康状况）",
        "input": {
            "query": "我昨天卧推时肩膀拉伤了，帮我调整计划",
            "user_profile": {
                "name": "调整A",
                "age": 28,
                "gender": "男",
                "height": 178,
                "weight": 75,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "available_equipment": ["杠铃", "哑铃", "龙门架"],
                "health_conditions": ["右肩拉伤(急性期)"],
            },
            "hard_constraints": ["禁止所有推类动作2周", "禁止肩部外展超过90度"],
        },
        "expected": {
            "policy_decision": "deny",  # harness 正确拒绝：模板缺少安全 guard
            "dag_should_execute": False,
        },
        "eval_dimensions": {
            "safety": "harness 阻止了缺少安全检查的执行（旧路径会放行）",
            "completeness": "N/A（被策略层拒绝）",
            "constraint_adherence": "N/A",
            "context_utilization": "health_conditions 被策略层正确识别",
            "tool_call_integrity": "N/A",
        },
    },
    {
        "id": "PA-02",
        "template": "plan_adjustment",
        "name": "时间变化调整",
        "description": "用户可用时间从60分钟缩短到30分钟",
        "input": {
            "query": "最近工作太忙，只有30分钟训练了，帮我调整",
            "user_profile": {
                "name": "调整B",
                "age": 35,
                "gender": "男",
                "height": 175,
                "weight": 72,
                "fitness_goal": "增肌",
                "experience_level": "高级",
                "available_equipment": ["杠铃", "哑铃", "龙门架", "各种器械"],
                "available_time": "30分钟",
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "verifier_checks": {
                "duration_exceeded": "调整后计划≤30分钟",
            },
        },
        "eval_dimensions": {
            "safety": "无安全问题",
            "completeness": "volume_calculator 重新计算",
            "constraint_adherence": "总时长≤30分钟",
            "context_utilization": "高级水平允许超级组等高效策略",
            "tool_call_integrity": "时间约束传入 program_designer",
        },
    },
    {
        "id": "PA-03",
        "template": "plan_adjustment",
        "name": "器械变化调整",
        "description": "用户从健身房转为家庭训练",
        "input": {
            "query": "我不去健身房了，在家只有哑铃和弹力带",
            "user_profile": {
                "name": "调整C",
                "age": 30,
                "gender": "女",
                "height": 165,
                "weight": 58,
                "fitness_goal": "塑形",
                "experience_level": "中级",
                "available_equipment": ["哑铃", "弹力带"],
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "verifier_checks": {
                "equipment_mismatch": "所有动作只用哑铃、弹力带或徒手",
            },
        },
        "eval_dimensions": {
            "safety": "无安全问题",
            "completeness": "exercise_alternative_finder 找到替代",
            "constraint_adherence": "无杠铃/器械动作",
            "context_utilization": "器械列表变化被识别",
            "tool_call_integrity": "替代搜索限定可用器械",
        },
    },
    {
        "id": "PA-04",
        "template": "plan_adjustment",
        "name": "疲劳反馈调整",
        "description": "用户反馈训练量过大，需要降低",
        "input": {
            "query": "最近训练后恢复不过来，太累了，帮我减量",
            "user_profile": {
                "name": "调整D",
                "age": 42,
                "gender": "男",
                "height": 172,
                "weight": 80,
                "fitness_goal": "增肌",
                "experience_level": "中级",
                "available_equipment": ["杠铃", "哑铃", "龙门架"],
                "available_time": "60分钟",
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "verifier_checks": {
                "volume_overload": "调整后训练量应低于当前",
            },
        },
        "eval_dimensions": {
            "safety": "减量不应引入新风险",
            "completeness": "volume_calculator 重新计算",
            "constraint_adherence": "训练量确实降低",
            "context_utilization": "疲劳反馈影响训练量决策",
            "tool_call_integrity": "减量参数正确传入",
        },
    },
    {
        "id": "PA-05",
        "template": "plan_adjustment",
        "name": "目标变化调整",
        "description": "用户从增肌转为减脂",
        "input": {
            "query": "我想从增肌转为减脂，帮我调整计划",
            "user_profile": {
                "name": "调整E",
                "age": 26,
                "gender": "男",
                "height": 180,
                "weight": 85,
                "fitness_goal": "减脂",  # 已更新
                "experience_level": "中级",
                "available_equipment": ["杠铃", "哑铃", "跑步机", "划船机"],
                "available_time": "60分钟",
            },
            "hard_constraints": [],
        },
        "expected": {
            "policy_decision": "allow",
            "dag_should_execute": True,
            "verifier_checks": {
                "goal_mismatch": "计划类型应匹配减脂目标",
            },
        },
        "eval_dimensions": {
            "safety": "无安全问题",
            "completeness": "正常执行",
            "constraint_adherence": "计划符合减脂目标",
            "context_utilization": "目标变化被识别并影响方案",
            "tool_call_integrity": "fitness_goal=减脂 正确传入",
        },
    },
]
