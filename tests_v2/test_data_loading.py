"""
test_data_loading.py — 数据层加载验证

验证：
- 向量索引正确加载（数量、维度）
- ID 映射与 payload 对齐
- 图谱加载且可查询
- 元数据加载且字段完整
"""

import pytest


class TestVectorIndex:
    """向量索引加载测试"""

    async def test_exercise_index_loaded(self, data_store):
        """动作向量索引已加载"""
        assert data_store.exercise_index is not None
        assert data_store.exercise_index.count > 0

    async def test_exercise_count_matches(self, data_store):
        """向量数 = ID 数 = Payload 数"""
        count = data_store.exercise_index.count
        assert len(data_store.exercise_ids) == count
        assert len(data_store.exercise_payloads) == count

    async def test_exercise_dimension(self, data_store):
        """向量维度 = 1024"""
        vec = data_store.exercise_index.get_vector(0)
        assert vec is not None
        assert vec.shape == (1024,)

    async def test_knowledge_index_loaded(self, data_store):
        """知识向量索引已加载"""
        assert data_store.knowledge_index is not None
        assert data_store.knowledge_index.count > 0

    async def test_food_index_loaded(self, data_store):
        """食物向量索引已加载"""
        assert data_store.food_index is not None
        assert data_store.food_index.count > 0


class TestIDMapping:
    """ID 映射测试"""

    async def test_exercise_ids_are_strings(self, data_store):
        """动作 ID 是字符串"""
        for eid in data_store.exercise_ids[:10]:
            assert isinstance(eid, str)

    async def test_exercise_ids_unique(self, data_store):
        """动作 ID 无重复"""
        assert len(set(data_store.exercise_ids)) == len(data_store.exercise_ids)

    async def test_payload_has_name(self, data_store):
        """Payload 包含 name_zh 字段"""
        for payload in data_store.exercise_payloads[:10]:
            assert "name_zh" in payload, f"Payload missing name_zh: {payload.get('id')}"


class TestGraphStore:
    """图谱加载测试"""

    async def test_graph_ready(self, data_store):
        """图谱已加载"""
        assert data_store.graph.ready

    async def test_graph_has_nodes(self, data_store):
        """图谱有节点"""
        assert data_store.graph.node_count > 0

    async def test_graph_has_edges(self, data_store):
        """图谱有边（至少某个节点有关系）"""
        # 用前 10 个动作 ID 检查是否有关系
        for eid in data_store.exercise_ids[:10]:
            relations = data_store.graph.get_all_relations(eid)
            if relations:
                return  # 找到至少一条边
        pytest.fail("No edges found for first 10 exercise IDs")

    async def test_graph_query_exercise(self, data_store):
        """可以查询动作的图谱关系"""
        # 用第一个动作 ID 测试
        eid = data_store.exercise_ids[0]
        relations = data_store.graph.get_relations(eid, "TARGETS_PRIMARY")
        # 不要求一定有结果，但不应报错
        assert isinstance(relations, list)


class TestMetadataStore:
    """元数据加载测试"""

    async def test_metadata_ready(self, data_store):
        """元数据已加载"""
        assert data_store.metadata.ready

    async def test_metadata_exercise_count(self, data_store):
        """元数据动作数 > 0"""
        all_ids = data_store.metadata.get_all_exercise_ids()
        assert len(all_ids) > 0

    async def test_metadata_exercise_fields(self, data_store):
        """元数据包含关键字段"""
        all_ids = data_store.metadata.get_all_exercise_ids()
        ex = data_store.metadata.get_exercise(all_ids[0])
        assert ex is not None
        assert "name_zh" in ex

    async def test_metadata_search_by_name(self, data_store):
        """按名称搜索元数据"""
        results = data_store.metadata.search_exercises_by_name("深蹲")
        assert len(results) > 0
        for r in results:
            assert "深蹲" in r.get("name_zh", "")
