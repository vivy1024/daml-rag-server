"""
DAML-RAG v3 浪潮引擎 — 单元测试

测试范围:
- 计算工具 (calculators.py)
- 数据加载 (loader.py)
- 向量索引 (vector_index.py)
- EPA (epa.py)
- 安全引擎 (safety_engine.py)
"""

import os
import sys
import pytest
import numpy as np

# 设置环境
os.environ.setdefault("DATA_DIR", os.path.join(os.path.dirname(__file__), "../../data/v3"))
os.environ.setdefault("EMBEDDING_API_KEY", "test")

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))


# === 计算工具测试 ===

class TestCalculateTDEE:
    """TDEE 计算测试"""

    def test_male_moderate(self):
        from src_v2.tools.calculators import calculate_tdee
        result = calculate_tdee("male", 25, 75, 178, "moderate", "maintain")
        assert 2500 < result["tdee"] < 3000
        assert result["bmr"] > 0
        assert result["target_calories"] == result["tdee"]  # maintain = no adjustment

    def test_female_lose_fat(self):
        from src_v2.tools.calculators import calculate_tdee
        result = calculate_tdee("female", 30, 60, 165, "light", "lose_fat")
        assert result["target_calories"] == result["tdee"] - 500
        assert result["macros"]["protein_g"] > 100  # 高蛋白减脂

    def test_bulk_surplus(self):
        from src_v2.tools.calculators import calculate_tdee
        result = calculate_tdee("male", 22, 70, 175, "active", "bulk")
        assert result["target_calories"] == result["tdee"] + 500

    def test_macros_sum(self):
        from src_v2.tools.calculators import calculate_tdee
        result = calculate_tdee("male", 25, 75, 178, "moderate", "maintain")
        macros = result["macros"]
        # 三大营养素比例之和应接近 100%
        total_ratio = macros["protein_ratio"] + macros["fat_ratio"] + macros["carbs_ratio"]
        assert 95 <= total_ratio <= 105  # 允许四舍五入误差


class TestCalculateTrainingVolume:
    """训练容量计算测试"""

    def test_chest_intermediate(self):
        from src_v2.tools.calculators import calculate_training_volume
        result = calculate_training_volume("胸", "intermediate", "hypertrophy")
        assert result["mev"] == 8
        assert result["mav"] == 14
        assert result["mrv"] == 20
        assert result["frequency_per_week"] == 2

    def test_beginner_lower_volume(self):
        from src_v2.tools.calculators import calculate_training_volume
        beginner = calculate_training_volume("背", "beginner")
        intermediate = calculate_training_volume("背", "intermediate")
        assert beginner["mav"] < intermediate["mav"]

    def test_chinese_muscle_names(self):
        from src_v2.tools.calculators import calculate_training_volume
        # 各种中文名都应该能识别
        for name in ["胸", "胸部", "胸大肌", "背", "背部", "肩", "腿"]:
            result = calculate_training_volume(name)
            assert result["mev"] > 0 or result["muscle_group_en"] in ("abs",)


class TestCalculate1RM:
    """1RM 估算测试"""

    def test_basic(self):
        from src_v2.tools.calculators import calculate_1rm
        result = calculate_1rm(100, 5)
        # Epley: 100 * (1 + 5/30) = 116.67
        assert abs(result["estimated_1rm"] - 116.7) < 0.1

    def test_single_rep(self):
        from src_v2.tools.calculators import calculate_1rm
        result = calculate_1rm(100, 1)
        assert result["estimated_1rm"] == 100.0

    def test_training_zones(self):
        from src_v2.tools.calculators import calculate_1rm
        result = calculate_1rm(100, 5)
        assert "strength" in result["training_zones"]
        assert "hypertrophy" in result["training_zones"]
        assert "endurance" in result["training_zones"]


class TestAssessStrengthLevel:
    """力量水平评估测试"""

    def test_bench_intermediate(self):
        from src_v2.tools.calculators import assess_strength_level
        # 75kg 体重卧推 100kg = 1.33x BW → intermediate
        result = assess_strength_level("卧推", 100, 75, "male")
        assert result["level"] == "intermediate"
        assert result["ratio"] == pytest.approx(1.33, abs=0.01)

    def test_squat_advanced(self):
        from src_v2.tools.calculators import assess_strength_level
        # 80kg 体重深蹲 160kg = 2.0x BW → advanced
        result = assess_strength_level("深蹲", 160, 80, "male")
        assert result["level"] == "advanced"

    def test_female_standards(self):
        from src_v2.tools.calculators import assess_strength_level
        # 女性标准更低
        result = assess_strength_level("卧推", 50, 60, "female")
        # 50/60 = 0.83x BW, 女性 intermediate 是 0.5x
        assert result["level"] in ("intermediate", "advanced")


class TestDesignTrainingSplit:
    """训练分化设计测试"""

    def test_3_days(self):
        from src_v2.tools.calculators import design_training_split
        result = design_training_split(3, "hypertrophy", "intermediate")
        assert result["days_per_week"] == 3
        assert len(result["schedule"]) >= 3

    def test_4_days(self):
        from src_v2.tools.calculators import design_training_split
        result = design_training_split(4, "hypertrophy", "intermediate")
        assert "上下" in result["split_name"] or "Upper" in result["split_name"]

    def test_6_days(self):
        from src_v2.tools.calculators import design_training_split
        result = design_training_split(6, "hypertrophy", "advanced")
        assert result["days_per_week"] == 6
        assert "PPL" in result["split_name"] or "推拉腿" in result["split_name"]


# === 向量索引测试 ===

class TestVectorIndex:
    """向量索引测试"""

    def test_numpy_search(self, tmp_path):
        from src_v2.engine.vector_index import VectorIndex
        # 创建小型测试数据并保存为 npy
        vectors = np.random.randn(100, 64).astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / norms

        npy_path = str(tmp_path / "test.npy")
        np.save(npy_path, vectors)

        index = VectorIndex(dimension=64, max_elements=100)
        index.load_from_npy(npy_path)

        assert index.count == 100

        # 搜索应返回自身为最相似
        results = index.search(vectors[0], k=5)
        assert len(results) == 5
        assert results[0][0] == 0  # 第一个结果应该是自身
        assert results[0][1] > 0.99  # 相似度接近 1

    def test_get_vector(self, tmp_path):
        from src_v2.engine.vector_index import VectorIndex
        vectors = np.random.randn(50, 32).astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        vectors = vectors / norms

        npy_path = str(tmp_path / "test.npy")
        np.save(npy_path, vectors)

        index = VectorIndex(dimension=32, max_elements=50)
        index.load_from_npy(npy_path)

        vec = index.get_vector(10)
        assert vec is not None
        assert np.allclose(vec, vectors[10], atol=1e-5)


# === EPA 测试 ===

class TestEPA:
    """EPA (Embedding Posture Analysis) 测试"""

    def test_basic_compute(self):
        from src_v2.engine.epa import compute_epa

        # 创建查询向量和 PCA 基底
        query = np.random.randn(64).astype(np.float32)
        query = query / np.linalg.norm(query)

        # PCA 基底 (4 components × 64 dim)
        pca_basis = np.random.randn(4, 64).astype(np.float32)
        pca_basis, _ = np.linalg.qr(pca_basis.T)
        pca_basis = pca_basis.T[:4]

        result = compute_epa(query, pca_basis)
        assert result is not None
        assert hasattr(result, "entropy")
        assert result.entropy >= 0
        assert hasattr(result, "dominant_axes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
