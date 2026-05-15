"""
src_v2/clients BackendClient + user_data 工具 — 单元测试

在容器内运行：
  docker exec fitness_daml_rag bash -c "cd /app && python -m pytest tests/unit/test_user_data_tools.py -v"
"""

import os
import sys
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ═══════════════════════════════════════════════════════════
# BackendClient 单元测试
# ═══════════════════════════════════════════════════════════

class TestBackendClient:
    """BackendClient 基础功能测试"""

    def test_validate_user_id_valid(self):
        from src_v2.clients import BackendClient
        client = BackendClient(base_url="http://test", token="x" * 32)
        assert client._validate_user_id("123") == "123"
        assert client._validate_user_id("abc-def_123") == "abc-def_123"

    def test_validate_user_id_invalid(self):
        from src_v2.clients import BackendClient
        client = BackendClient(base_url="http://test", token="x" * 32)
        with pytest.raises(ValueError):
            client._validate_user_id("../etc/passwd")
        with pytest.raises(ValueError):
            client._validate_user_id("1; DROP TABLE")
        with pytest.raises(ValueError):
            client._validate_user_id("")

    def test_default_config(self):
        from src_v2.clients import BackendClient, BACKEND_BASE_URL, INTERNAL_API_TOKEN
        client = BackendClient()
        assert client.base_url == BACKEND_BASE_URL.rstrip("/")
        assert client.token == INTERNAL_API_TOKEN


# ═══════════════════════════════════════════════════════════
# user_data 工具单元测试（mock BackendClient）
# ═══════════════════════════════════════════════════════════

class TestGetUserProfile:
    """get_user_profile 工具测试"""

    @pytest.mark.asyncio
    async def test_success(self):
        from src_v2.tools.user_data import get_user_profile

        mock_data = {
            "user_id": 1,
            "basic": {"age": 25, "gender": "male", "height_cm": 175, "weight_kg": 70},
            "goals": {"primary_goal": "muscle_gain"},
            "health": {"injuries": [], "conditions": []},
            "training": {"level": "intermediate"},
            "strength": {"bench_press_1rm": 80},
        }

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_user_profile.return_value = mock_data
            mock_get.return_value = mock_client

            result = await get_user_profile("1")

            assert result["user_id"] == 1
            assert result["basic"]["age"] == 25
            assert result["goals"]["primary_goal"] == "muscle_gain"

    @pytest.mark.asyncio
    async def test_not_found_returns_fallback(self):
        from src_v2.tools.user_data import get_user_profile

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_user_profile.return_value = None
            mock_get.return_value = mock_client

            result = await get_user_profile("999")

            assert "error" in result
            assert "fallback_hint" in result
            assert "询问用户" in result["fallback_hint"]


class TestGetTrainingHistory:
    """get_training_history 工具测试"""

    @pytest.mark.asyncio
    async def test_success(self):
        from src_v2.tools.user_data import get_training_history

        mock_data = {
            "user_id": 1,
            "days": 30,
            "total_sessions": 12,
            "records": [
                {"session_date": "2026-05-10", "exercises": [{"exercise_name": "卧推", "sets": 4}]}
            ],
        }

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_training_records.return_value = mock_data
            mock_get.return_value = mock_client

            result = await get_training_history("1", days=30)

            assert result["total_sessions"] == 12
            assert len(result["records"]) == 1

    @pytest.mark.asyncio
    async def test_no_records_returns_fallback(self):
        from src_v2.tools.user_data import get_training_history

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_training_records.return_value = None
            mock_get.return_value = mock_client

            result = await get_training_history("1")

            assert "error" in result
            assert "fallback_hint" in result


class TestGetProgressData:
    """get_progress_data 工具测试"""

    @pytest.mark.asyncio
    async def test_success(self):
        from src_v2.tools.user_data import get_progress_data

        mock_data = {
            "metric": "weight",
            "data_points": [{"date": "2026-05-01", "value": 75}],
            "trend": "stable",
        }

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_progress_data.return_value = mock_data
            mock_get.return_value = mock_client

            result = await get_progress_data("1", metric="weight")

            assert result["metric"] == "weight"
            assert result["trend"] == "stable"

    @pytest.mark.asyncio
    async def test_no_data_returns_fallback(self):
        from src_v2.tools.user_data import get_progress_data

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.get_progress_data.return_value = None
            mock_get.return_value = mock_client

            result = await get_progress_data("1")

            assert "error" in result
            assert "fallback_hint" in result


class TestSaveTrainingPlan:
    """save_training_plan 工具测试"""

    @pytest.mark.asyncio
    async def test_success(self):
        from src_v2.tools.user_data import save_training_plan

        mock_data = {"plan_id": 42, "status": "saved"}

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.save_training_plan.return_value = mock_data
            mock_get.return_value = mock_client

            result = await save_training_plan("1", {"name": "增肌计划", "days": 4})

            assert result["plan_id"] == 42

    @pytest.mark.asyncio
    async def test_save_failure_returns_fallback(self):
        from src_v2.tools.user_data import save_training_plan

        with patch("src_v2.tools.user_data.get_backend_client") as mock_get:
            mock_client = AsyncMock()
            mock_client.save_training_plan.return_value = None
            mock_get.return_value = mock_client

            result = await save_training_plan("1", {"name": "test"})

            assert "error" in result
            assert "fallback_hint" in result
