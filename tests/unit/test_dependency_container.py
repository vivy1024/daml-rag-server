# -*- coding: utf-8 -*-
"""
DependencyContainer - 单元测试

验证：
- 实例注册和获取
- 工厂函数延迟初始化
- 未注册依赖的错误处理
- reset清空
- 全局容器单例

Task 46 - Phase 7 Batch 4
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from framework.core.container import (
    DependencyContainer, get_container, reset_container,
)


class TestDependencyContainer:
    def setup_method(self):
        self.container = DependencyContainer()

    def test_register_and_get(self):
        self.container.register("db", "mock_db_client")
        assert self.container.get("db") == "mock_db_client"

    def test_register_factory_lazy_init(self):
        call_count = 0

        def factory():
            nonlocal call_count
            call_count += 1
            return "lazy_instance"

        self.container.register_factory("service", factory)
        assert call_count == 0  # 注册时不调用
        result = self.container.get("service")
        assert result == "lazy_instance"
        assert call_count == 1
        # 第二次获取不再调用工厂
        self.container.get("service")
        assert call_count == 1

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="未注册的依赖"):
            self.container.get("nonexistent")

    def test_get_or_none(self):
        assert self.container.get_or_none("missing") is None
        self.container.register("found", 42)
        assert self.container.get_or_none("found") == 42

    def test_has(self):
        assert self.container.has("x") is False
        self.container.register("x", 1)
        assert self.container.has("x") is True

    def test_has_factory(self):
        self.container.register_factory("y", lambda: 2)
        assert self.container.has("y") is True

    def test_reset(self):
        self.container.register("a", 1)
        self.container.register_factory("b", lambda: 2)
        self.container.reset()
        assert self.container.has("a") is False
        assert self.container.has("b") is False

    def test_registered_names(self):
        self.container.register("c", 3)
        self.container.register_factory("a", lambda: 1)
        self.container.register("b", 2)
        assert self.container.registered_names == ["a", "b", "c"]

    def test_instance_overrides_factory(self):
        """直接注册的实例优先于工厂"""
        self.container.register_factory("svc", lambda: "from_factory")
        self.container.register("svc", "direct")
        assert self.container.get("svc") == "direct"

    def test_factory_error_propagates(self):
        def bad_factory():
            raise RuntimeError("init failed")

        self.container.register_factory("bad", bad_factory)
        with pytest.raises(RuntimeError, match="init failed"):
            self.container.get("bad")


class TestGlobalContainer:
    def test_get_container_returns_same(self):
        c1 = get_container()
        c2 = get_container()
        assert c1 is c2

    def test_reset_creates_new(self):
        c1 = get_container()
        c1.register("test_key", "test_val")
        reset_container()
        c2 = get_container()
        assert c2.has("test_key") is False
