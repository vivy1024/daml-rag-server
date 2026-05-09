# -*- coding: utf-8 -*-
"""
Thread Routes 单元测试

测试内容：
- POST /api/v1/thread/create - 创建线程
- GET /api/v1/thread/list?user_id=X - 列出线程
- DELETE /api/v1/thread/{thread_id} - 删除线程
"""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.routes.thread import router, _thread_store


@pytest.fixture
def client():
    """创建测试用 FastAPI 客户端"""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_store():
    """每个测试前清空线程存储"""
    _thread_store.clear()
    yield
    _thread_store.clear()


class TestCreateThread:
    """POST /api/v1/thread/create 测试"""

    def test_create_thread_success(self, client):
        """正常创建线程"""
        resp = client.post(
            "/api/v1/thread/create",
            json={"user_id": "user-001", "title": "测试对话"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "thread_id" in data
        assert "created_at" in data
        assert len(data["thread_id"]) == 36  # UUID 格式

    def test_create_thread_without_title(self, client):
        """不提供标题时应自动生成"""
        resp = client.post(
            "/api/v1/thread/create",
            json={"user_id": "user-001"},
        )
        assert resp.status_code == 200
        assert "thread_id" in resp.json()

    def test_create_thread_missing_user_id(self, client):
        """缺少 user_id 应返回 422"""
        resp = client.post("/api/v1/thread/create", json={})
        assert resp.status_code == 422

    def test_create_thread_empty_user_id(self, client):
        """空 user_id 应返回 422"""
        resp = client.post(
            "/api/v1/thread/create", json={"user_id": ""}
        )
        assert resp.status_code == 422

    def test_create_thread_with_metadata(self, client):
        """带元数据创建线程"""
        resp = client.post(
            "/api/v1/thread/create",
            json={
                "user_id": "user-001",
                "title": "带元数据",
                "metadata": {"source": "ios_app"},
            },
        )
        assert resp.status_code == 200


class TestListThreads:
    """GET /api/v1/thread/list 测试"""

    def test_list_empty(self, client):
        """无线程时应返回空列表"""
        resp = client.get("/api/v1/thread/list", params={"user_id": "user-001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["threads"] == []
        assert data["total"] == 0

    def test_list_after_create(self, client):
        """创建后应能列出线程"""
        client.post("/api/v1/thread/create", json={"user_id": "user-001"})
        client.post("/api/v1/thread/create", json={"user_id": "user-001"})
        client.post("/api/v1/thread/create", json={"user_id": "user-002"})

        resp = client.get("/api/v1/thread/list", params={"user_id": "user-001"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert len(data["threads"]) == 2

    def test_list_filters_by_user(self, client):
        """应只返回指定用户的线程"""
        client.post("/api/v1/thread/create", json={"user_id": "user-001"})
        client.post("/api/v1/thread/create", json={"user_id": "user-002"})

        resp = client.get("/api/v1/thread/list", params={"user_id": "user-002"})
        data = resp.json()
        assert data["total"] == 1

    def test_list_missing_user_id(self, client):
        """缺少 user_id 参数应返回 422"""
        resp = client.get("/api/v1/thread/list")
        assert resp.status_code == 422


class TestDeleteThread:
    """DELETE /api/v1/thread/{thread_id} 测试"""

    def test_delete_existing_thread(self, client):
        """删除已存在的线程"""
        create_resp = client.post(
            "/api/v1/thread/create", json={"user_id": "user-001"}
        )
        thread_id = create_resp.json()["thread_id"]

        resp = client.delete(f"/api/v1/thread/{thread_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["thread_id"] == thread_id
        assert data["deleted"] is True

        # 确认已删除
        list_resp = client.get(
            "/api/v1/thread/list", params={"user_id": "user-001"}
        )
        assert list_resp.json()["total"] == 0

    def test_delete_nonexistent_thread(self, client):
        """删除不存在的线程应返回 404"""
        resp = client.delete("/api/v1/thread/nonexistent-id")
        assert resp.status_code == 404