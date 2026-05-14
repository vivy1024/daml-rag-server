"""
图谱专项查询工具 — 单元测试

在容器内运行：
  docker exec fitness_daml_rag bash -c "DATA_DIR=/app/data/v3 python -m pytest tests/unit/test_graph_queries.py -v"
"""

import os
import sys
import json
import pytest

os.environ["DATA_DIR"] = "/app/data/v3"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture(scope="module")
def graph():
    """加载真实图谱"""
    from src_v2.data.graph_store import GraphStore
    from src_v2.config import get_config
    import src_v2.config as cfg_mod
    cfg_mod._config = None

    cfg = get_config()
    g = GraphStore()
    graph_path = os.path.join(cfg.data.graph_dir, "exercise_graph.json")
    if os.path.exists(graph_path):
        g.load_from_json(graph_path)
    return g


class TestGetContraindications:
    """禁忌症查询测试"""

    def test_lumbar_disc(self, graph):
        from src_v2.tools.graph_queries import get_contraindications

        result = get_contraindications(["腰椎间盘突出"], graph)

        assert result["total_blocked"] > 0
        assert "腰椎间盘突出" in result["injuries_matched"] or any(
            "腰椎" in m for m in result["injuries_matched"]
        )
        # 应该有禁忌动作
        exercises = [c["exercise"] for c in result["contraindicated"]]
        assert len(exercises) > 5

    def test_shoulder_injury(self, graph):
        from src_v2.tools.graph_queries import get_contraindications

        result = get_contraindications(["肩袖损伤"], graph)

        assert result["total_blocked"] > 0
        assert any("肩" in m for m in result["injuries_matched"])

    def test_multiple_injuries(self, graph):
        from src_v2.tools.graph_queries import get_contraindications

        result = get_contraindications(["腰椎间盘突出", "膝关节损伤"], graph)

        assert result["total_blocked"] > 0
        assert len(result["injuries_matched"]) >= 1

    def test_unknown_injury(self, graph):
        from src_v2.tools.graph_queries import get_contraindications

        result = get_contraindications(["不存在的伤病xyz"], graph)

        assert result["total_blocked"] == 0
        assert "note" in result

    def test_alternatives_provided(self, graph):
        from src_v2.tools.graph_queries import get_contraindications

        result = get_contraindications(["肩袖损伤"], graph)

        # 至少部分禁忌动作应该有替代建议
        has_alternatives = any(
            len(c.get("alternatives", [])) > 0
            for c in result["contraindicated"]
        )
        assert has_alternatives, "应该为禁忌动作提供替代方案"


class TestGetPostureCorrections:
    """体态矫正查询测试"""

    def test_round_shoulders(self, graph):
        from src_v2.tools.graph_queries import get_posture_corrections

        result = get_posture_corrections("圆肩", graph)

        # 可能找到也可能没有（取决于图谱数据）
        if result.get("note"):
            # 没找到节点，检查 fallback_hint
            assert "fallback_hint" in result
        else:
            assert result["issue"] == "圆肩"

    def test_anterior_pelvic_tilt(self, graph):
        from src_v2.tools.graph_queries import get_posture_corrections

        result = get_posture_corrections("骨盆前倾", graph)

        if not result.get("note"):
            assert isinstance(result["correction_exercises"], list)
            assert isinstance(result["avoid_exercises"], list)

    def test_unknown_issue(self, graph):
        from src_v2.tools.graph_queries import get_posture_corrections

        result = get_posture_corrections("不存在的体态问题", graph)

        assert result.get("note") or result.get("fallback_hint")


class TestGetRehabilitationProtocol:
    """康复协议查询测试"""

    def test_shoulder_injury_rehab(self, graph):
        from src_v2.tools.graph_queries import get_rehabilitation_protocol

        result = get_rehabilitation_protocol("肩袖损伤", graph=graph)

        assert result["injury"] == "肩袖损伤"
        assert result["total_contraindicated"] > 0
        assert isinstance(result["contraindicated_exercises"], list)
        assert isinstance(result["safe_exercises_beginner"], list)

    def test_unknown_injury_rehab(self, graph):
        from src_v2.tools.graph_queries import get_rehabilitation_protocol

        result = get_rehabilitation_protocol("不存在的伤病", graph=graph)

        assert "fallback_hint" in result


class TestGetMuscleExerciseMap:
    """肌群动作映射测试"""

    def test_chest(self, graph):
        from src_v2.tools.graph_queries import get_muscle_exercise_map

        result = get_muscle_exercise_map("胸", graph)

        if result.get("note"):
            # 可能肌群名不完全匹配
            pass
        else:
            assert result["total"] > 0
            assert len(result["primary_exercises"]) > 0

    def test_biceps(self, graph):
        from src_v2.tools.graph_queries import get_muscle_exercise_map

        result = get_muscle_exercise_map("肱二头肌", graph)

        assert result["total"] > 0
        assert len(result["primary_exercises"]) > 0

    def test_with_equipment_filter(self, graph):
        from src_v2.tools.graph_queries import get_muscle_exercise_map

        result_all = get_muscle_exercise_map("肱二头肌", graph)
        result_dumbbell = get_muscle_exercise_map("肱二头肌", graph, equipment="哑铃")

        # 过滤后应该更少
        assert result_dumbbell["total"] <= result_all["total"]

    def test_unknown_muscle(self, graph):
        from src_v2.tools.graph_queries import get_muscle_exercise_map

        result = get_muscle_exercise_map("不存在的肌群", graph)

        assert result["total"] == 0
        assert "fallback_hint" in result
