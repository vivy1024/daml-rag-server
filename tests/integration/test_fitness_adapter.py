# -*- coding: utf-8 -*-
"""
FitnessAdapter 集成测试 (REQ-8)

测试 FitnessAdapter 的公开 API、领域数据方法及与三层检索引擎的集成。
使用 pytest + unittest.mock 模拟外部依赖。
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.applications.fitness.fitness_adapter import (
    FitnessAdapter,
    get_fitness_adapter,
    initialize_fitness_adapter,
    FITNESS_LAYER3_RULES,
    FITNESS_DAG_TEMPLATES,
    FITNESS_TOOLS,
)
from src.framework.adapters.domain_adapter import (
    RuleCategory,
    RuleSeverity,
    Layer3Rule,
    DAGTemplateDefinition,
    ToolDefinition,
)


class TestFitnessAdapterBasic:
    """FitnessAdapter 基础 API 测试"""

    def test_get_name(self):
        adapter = FitnessAdapter()
        assert adapter.get_name() == "fitness"

    def test_get_display_name(self):
        adapter = FitnessAdapter()
        assert adapter.get_display_name() == "健身"

    def test_get_description(self):
        adapter = FitnessAdapter()
        desc = adapter.get_description()
        assert "健身" in desc
        assert "Layer3" in desc or "规则" in desc

    def test_get_version(self):
        adapter = FitnessAdapter()
        assert adapter.get_version() == "1.0.0"

    def test_get_layer3_rules_returns_copy(self):
        adapter = FitnessAdapter()
        rules = adapter.get_layer3_rules()
        assert len(rules) == len(FITNESS_LAYER3_RULES)
        assert rules is not FITNESS_LAYER3_RULES

    def test_get_dag_templates_returns_copy(self):
        adapter = FitnessAdapter()
        templates = adapter.get_dag_templates()
        assert len(templates) == len(FITNESS_DAG_TEMPLATES)
        assert templates is not FITNESS_DAG_TEMPLATES

    def test_get_tools_returns_copy(self):
        adapter = FitnessAdapter()
        tools = adapter.get_tools()
        assert len(tools) == len(FITNESS_TOOLS)
        assert tools is not FITNESS_TOOLS


class TestFitnessAdapterRules:
    """Layer3 规则相关测试"""

    def test_get_safety_rules(self):
        adapter = FitnessAdapter()
        rules = adapter.get_safety_rules()
        assert all(r.category == RuleCategory.SAFETY for r in rules)

    def test_get_kinetic_rules(self):
        adapter = FitnessAdapter()
        rules = adapter.get_kinetic_rules()
        assert all(r.category == RuleCategory.KINETIC for r in rules)

    def test_get_recovery_rules(self):
        adapter = FitnessAdapter()
        rules = adapter.get_recovery_rules()
        assert all(r.category == RuleCategory.RECOVERY for r in rules)

    def test_get_domain_rules(self):
        adapter = FitnessAdapter()
        rules = adapter.get_domain_rules()
        assert all(r.category == RuleCategory.DOMAIN for r in rules)

    def test_get_rule_by_id(self):
        adapter = FitnessAdapter()
        rule = adapter.get_rule_by_id("joint_load_rule")
        assert rule is not None
        assert rule.rule_id == "joint_load_rule"
        assert rule.category == RuleCategory.SAFETY

    def test_get_rule_by_id_not_found(self):
        adapter = FitnessAdapter()
        assert adapter.get_rule_by_id("nonexistent") is None


class TestFitnessAdapterTemplates:
    """DAG 模板相关测试"""

    def test_get_training_templates(self):
        adapter = FitnessAdapter()
        templates = adapter.get_training_templates()
        assert all(t.category == "training" for t in templates)

    def test_get_nutrition_templates(self):
        adapter = FitnessAdapter()
        templates = adapter.get_nutrition_templates()
        assert all(t.category == "nutrition" for t in templates)

    def test_get_safety_templates(self):
        adapter = FitnessAdapter()
        templates = adapter.get_safety_templates()
        assert all(t.category == "safety" for t in templates)

    def test_get_comprehensive_templates(self):
        adapter = FitnessAdapter()
        templates = adapter.get_comprehensive_templates()
        assert all(t.category == "comprehensive" for t in templates)

    def test_match_template_by_intent_greeting(self):
        adapter = FitnessAdapter()
        template = adapter.match_template_by_intent("你好")
        assert template is not None
        assert template.template_id == "greeting"

    def test_match_template_by_intent_training_plan(self):
        adapter = FitnessAdapter()
        template = adapter.match_template_by_intent("制定训练计划")
        assert template is not None
        assert template.template_id == "complete_training_plan"

    def test_match_template_by_intent_no_match(self):
        adapter = FitnessAdapter()
        assert adapter.match_template_by_intent("无关内容xyz") is None

    def test_get_template_by_id(self):
        adapter = FitnessAdapter()
        tpl = adapter.get_template_by_id("greeting")
        assert tpl is not None
        assert tpl.template_id == "greeting"


class TestFitnessAdapterTools:
    """MCP 工具相关测试"""

    def test_get_exercise_tools(self):
        adapter = FitnessAdapter()
        tools = adapter.get_exercise_tools()
        assert all(t.category == "exercise" for t in tools)

    def test_get_safety_tools(self):
        adapter = FitnessAdapter()
        tools = adapter.get_safety_tools()
        assert all(t.category == "safety" for t in tools)

    def test_get_training_tools(self):
        adapter = FitnessAdapter()
        tools = adapter.get_training_tools()
        assert all(t.category == "training" for t in tools)

    def test_get_nutrition_tools(self):
        adapter = FitnessAdapter()
        tools = adapter.get_nutrition_tools()
        assert all(t.category == "nutrition" for t in tools)

    def test_get_p0_tools(self):
        adapter = FitnessAdapter()
        tools = adapter.get_p0_tools()
        assert all(t.priority == "P0" for t in tools)

    def test_get_p1_tools(self):
        adapter = FitnessAdapter()
        tools = adapter.get_p1_tools()
        assert all(t.priority == "P1" for t in tools)

    def test_get_tool_by_name(self):
        adapter = FitnessAdapter()
        tool = adapter.get_tool_by_name("intelligent_exercise_selector")
        assert tool is not None
        assert tool.name == "intelligent_exercise_selector"


class TestFitnessAdapterDomainData:
    """领域数据方法测试（降级、关键词、安全等）"""

    def test_get_fallback_recommendations(self):
        adapter = FitnessAdapter()
        recs = adapter.get_fallback_recommendations()
        assert "胸" in recs
        assert "背" in recs
        assert "腿" in recs
        for key, items in recs.items():
            assert isinstance(items, list)
            for item in items:
                assert "exercise_name_zh" in item or "name" in item

    def test_get_keyword_mapping(self):
        adapter = FitnessAdapter()
        mapping = adapter.get_keyword_mapping()
        assert "胸" in mapping
        assert "背" in mapping
        for key, synonyms in mapping.items():
            assert isinstance(synonyms, list)

    def test_get_safety_contraindications(self):
        adapter = FitnessAdapter()
        contra = adapter.get_safety_contraindications()
        assert "骨盆前倾" in contra
        assert "圆肩" in contra

    def test_get_joint_keywords(self):
        adapter = FitnessAdapter()
        keywords = adapter.get_joint_keywords()
        assert "肩" in keywords
        assert "膝" in keywords
        assert "腰" in keywords

    def test_get_default_fallback_items(self):
        adapter = FitnessAdapter()
        items = adapter.get_default_fallback_items()
        assert len(items) >= 1
        for item in items:
            assert "exercise_name_zh" in item or "source" in item

    def test_get_cypher_templates(self):
        adapter = FitnessAdapter()
        templates = adapter.get_cypher_templates()
        assert "entity_search" in templates
        assert "entity_search_with_filter" in templates
        assert "$keyword" in templates["entity_search"]

    def test_get_cypher_result_mapping(self):
        adapter = FitnessAdapter()
        mapping = adapter.get_cypher_result_mapping()
        assert "exercise_zh" in mapping
        assert mapping["exercise_zh"] == "exercise_name_zh"


class TestFitnessAdapterInitialization:
    """初始化与便捷函数测试"""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        adapter = FitnessAdapter()
        result = await adapter.initialize()
        assert result is True
        assert adapter.is_initialized()

    @pytest.mark.asyncio
    async def test_initialize_fitness_adapter(self):
        adapter = await initialize_fitness_adapter()
        assert isinstance(adapter, FitnessAdapter)
        assert adapter.is_initialized()

    def test_get_fitness_adapter(self):
        adapter = get_fitness_adapter()
        assert isinstance(adapter, FitnessAdapter)


class TestFitnessAdapterIntegration:
    """与三层检索引擎等组件的集成测试（Mock 外部依赖）"""

    @pytest.mark.asyncio
    async def test_rule_based_fallback_uses_adapter_data(self):
        from src.framework.retrieval.three_layer.fallback import FallbackMixin
        from src.framework.retrieval.three_layer.models import LayerExecutionResult

        adapter = FitnessAdapter()

        class EngineWithFallback(FallbackMixin):
            pass

        engine = EngineWithFallback()
        engine.domain_adapter = adapter
        engine._empty_layer_result = lambda self, name, err=None: LayerExecutionResult(
            layer_name=name, success=False, results=[], execution_time_ms=0, confidence=0, error=err
        )
        from types import MethodType
        engine._empty_layer_result = MethodType(
            lambda self, name, err=None: LayerExecutionResult(
                layer_name=name, success=False, results=[], execution_time_ms=0, confidence=0, error=err
            ),
            engine,
        )

        result = await engine._execute_rule_based_fallback(
            query="练胸",
            user_profile={"fitness_level": "intermediate"},
            top_k=5,
        )
        assert result.success
        assert len(result.results) > 0

    @pytest.mark.asyncio
    async def test_keyword_extraction_for_layer2(self):
        adapter = FitnessAdapter()
        mapping = adapter.get_keyword_mapping()
        query = "我想练胸大肌和背部"
        keywords = []
        query_lower = query.lower()
        for key, synonyms in mapping.items():
            if key in query or any(s.lower() in query_lower for s in synonyms):
                keywords.extend(synonyms)
        keywords = list(set(keywords))
        assert len(keywords) > 0
        assert any("胸" in k or "背" in k for k in keywords)
