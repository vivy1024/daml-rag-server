# -*- coding: utf-8 -*-
"""
LLM 模型池管理器

提供统一的多模型管理能力：
- 支持国产模型配置（DeepSeek/GLM/Qwen/Moonshot）
- 环境变量热切换（PRIMARY_MODEL、PRIMARY_BASE_URL、PRIMARY_API_KEY、FALLBACK_MODELS）
- 健康检查 + 自动降级
- fallback 链：主模型 → 备用模型 → 模板兜底

版本：v1.0.0
更新日期：2026-03-15
"""

import os
import time
import logging
import asyncio
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class ModelProvider(str, Enum):
    """支持的模型提供商"""
    DEEPSEEK = "deepseek"
    GLM = "glm"
    QWEN = "qwen"
    MOONSHOT = "moonshot"
    OPENAI_COMPATIBLE = "openai_compatible"


class ModelStatus(str, Enum):
    """模型健康状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class LLMModelConfig:
    """单个 LLM 模型配置"""
    name: str
    base_url: str
    api_key: str
    provider: ModelProvider = ModelProvider.OPENAI_COMPATIBLE
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_ms: int = 120000
    # 健康检查状态
    status: ModelStatus = ModelStatus.HEALTHY
    last_check_time: float = 0.0
    consecutive_failures: int = 0
    max_failures_before_degrade: int = 3


@dataclass
class LLMPoolConfig:
    """LLM 模型池配置（从环境变量加载）"""
    primary_model: str = ""
    primary_base_url: str = ""
    primary_api_key: str = ""
    primary_provider: ModelProvider = ModelProvider.OPENAI_COMPATIBLE
    fallback_models_raw: str = ""  # JSON 格式的备用模型列表
    health_check_interval_s: float = 60.0
    template_fallback_enabled: bool = True

    @classmethod
    def from_env(cls) -> "LLMPoolConfig":
        """从环境变量加载配置"""
        return cls(
            primary_model=os.getenv("PRIMARY_MODEL", "deepseek-chat"),
            primary_base_url=os.getenv("PRIMARY_BASE_URL", "https://api.deepseek.com/v1"),
            primary_api_key=os.getenv("PRIMARY_API_KEY", ""),
            primary_provider=ModelProvider(
                os.getenv("PRIMARY_PROVIDER", "deepseek")
            ),
            fallback_models_raw=os.getenv("FALLBACK_MODELS", ""),
            health_check_interval_s=float(
                os.getenv("LLM_HEALTH_CHECK_INTERVAL", "60")
            ),
            template_fallback_enabled=os.getenv(
                "TEMPLATE_FALLBACK_ENABLED", "true"
            ).lower() == "true",
        )


class LLMPoolManager:
    """
    LLM 模型池管理器

    职责：
    1. 管理主模型 + 备用模型列表
    2. 健康检查（异步心跳）
    3. 自动降级：主模型不可用时切换到备用模型
    4. 模板兜底：所有模型不可用时返回预设模板响应
    """

    def __init__(self, config: Optional[LLMPoolConfig] = None):
        self._config = config or LLMPoolConfig.from_env()
        self._primary: Optional[LLMModelConfig] = None
        self._fallbacks: list[LLMModelConfig] = []
        self._initialized = False
        self._health_check_task: Optional[asyncio.Task] = None
        self._load_models()

    def _load_models(self) -> None:
        """从配置加载模型列表"""
        # 主模型
        if self._config.primary_api_key:
            self._primary = LLMModelConfig(
                name=self._config.primary_model,
                base_url=self._config.primary_base_url,
                api_key=self._config.primary_api_key,
                provider=self._config.primary_provider,
            )

        # 备用模型（从 JSON 环境变量解析）
        self._fallbacks = self._parse_fallback_models(
            self._config.fallback_models_raw
        )
        self._initialized = True
        logger.info(
            "LLMPoolManager 初始化完成: primary=%s, fallbacks=%d",
            self._config.primary_model,
            len(self._fallbacks),
        )

    @staticmethod
    def _parse_fallback_models(raw: str) -> list[LLMModelConfig]:
        """
        解析 FALLBACK_MODELS 环境变量

        格式: JSON 数组，每项包含 name, base_url, api_key, provider
        示例: [{"name":"glm-4","base_url":"https://open.bigmodel.cn/api/paas/v4",
                "api_key":"xxx","provider":"glm"}]
        """
        if not raw or not raw.strip():
            return []
        import json
        try:
            items = json.loads(raw)
            models = []
            for item in items:
                models.append(LLMModelConfig(
                    name=item["name"],
                    base_url=item["base_url"],
                    api_key=item["api_key"],
                    provider=ModelProvider(item.get("provider", "openai_compatible")),
                    max_tokens=item.get("max_tokens", 4096),
                    temperature=item.get("temperature", 0.7),
                ))
            return models
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("解析 FALLBACK_MODELS 失败: %s", e)
            return []

    # ============ 模型获取 ============

    def get_active_model(self) -> Optional[LLMModelConfig]:
        """
        获取当前可用的最优模型

        降级链：主模型 → 备用模型（按顺序）→ None（触发模板兜底）
        """
        # 尝试主模型
        if self._primary and self._primary.status == ModelStatus.HEALTHY:
            return self._primary

        # 尝试备用模型
        for model in self._fallbacks:
            if model.status == ModelStatus.HEALTHY:
                logger.info("主模型不可用，降级到: %s", model.name)
                return model

        # 所有模型不可用
        logger.warning("所有 LLM 模型不可用，将使用模板兜底")
        return None

    @property
    def is_template_fallback(self) -> bool:
        """当前是否处于模板兜底状态"""
        return self.get_active_model() is None

    @property
    def primary_model(self) -> Optional[LLMModelConfig]:
        """获取主模型配置"""
        return self._primary

    @property
    def fallback_models(self) -> list[LLMModelConfig]:
        """获取备用模型列表"""
        return self._fallbacks.copy()

    @property
    def all_models(self) -> list[LLMModelConfig]:
        """获取所有模型（主 + 备用）"""
        models = []
        if self._primary:
            models.append(self._primary)
        models.extend(self._fallbacks)
        return models

    # ============ 健康检查 ============

    async def health_check(self, model: LLMModelConfig) -> bool:
        """
        对单个模型执行健康检查

        通过向 /models 端点发送 GET 请求验证连通性
        """
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(10.0)
            ) as client:
                url = f"{model.base_url.rstrip('/')}/models"
                headers = {"Authorization": f"Bearer {model.api_key}"}
                resp = await client.get(url, headers=headers)
                is_healthy = resp.status_code in (200, 401, 403)
                # 401/403 说明网络可达，API key 问题不影响连通性判断
                return is_healthy
        except (httpx.TimeoutException, httpx.ConnectError, OSError) as e:
            logger.debug("健康检查失败 [%s]: %s", model.name, e)
            return False

    async def check_all_models(self) -> dict[str, ModelStatus]:
        """对所有模型执行健康检查，更新状态"""
        results: dict[str, ModelStatus] = {}
        for model in self.all_models:
            healthy = await self.health_check(model)
            now = time.time()
            model.last_check_time = now

            if healthy:
                model.consecutive_failures = 0
                model.status = ModelStatus.HEALTHY
            else:
                model.consecutive_failures += 1
                if model.consecutive_failures >= model.max_failures_before_degrade:
                    model.status = ModelStatus.UNAVAILABLE
                else:
                    model.status = ModelStatus.DEGRADED

            results[model.name] = model.status
        return results

    def report_failure(self, model_name: str) -> None:
        """报告模型调用失败（由调用方在请求失败时调用）"""
        for model in self.all_models:
            if model.name == model_name:
                model.consecutive_failures += 1
                if model.consecutive_failures >= model.max_failures_before_degrade:
                    model.status = ModelStatus.UNAVAILABLE
                    logger.warning(
                        "模型 %s 连续失败 %d 次，标记为不可用",
                        model_name, model.consecutive_failures,
                    )
                break

    def report_success(self, model_name: str) -> None:
        """报告模型调用成功（重置失败计数）"""
        for model in self.all_models:
            if model.name == model_name:
                model.consecutive_failures = 0
                model.status = ModelStatus.HEALTHY
                break

    # ============ 后台健康检查任务 ============

    async def start_health_check_loop(self) -> None:
        """启动后台健康检查循环"""
        if self._health_check_task is not None:
            return
        self._health_check_task = asyncio.create_task(
            self._health_check_loop()
        )
        logger.info("LLM 健康检查后台任务已启动")

    async def _health_check_loop(self) -> None:
        """健康检查循环（后台运行）"""
        while True:
            try:
                await self.check_all_models()
            except Exception as e:
                logger.error("健康检查循环异常: %s", e)
            await asyncio.sleep(self._config.health_check_interval_s)

    async def stop_health_check_loop(self) -> None:
        """停止后台健康检查"""
        if self._health_check_task:
            self._health_check_task.cancel()
            self._health_check_task = None
            logger.info("LLM 健康检查后台任务已停止")

    # ============ 热重载 ============

    def reload_from_env(self) -> None:
        """从环境变量热重载配置（支持运行时切换模型）"""
        new_config = LLMPoolConfig.from_env()
        if (
            new_config.primary_model != self._config.primary_model
            or new_config.primary_base_url != self._config.primary_base_url
            or new_config.primary_api_key != self._config.primary_api_key
        ):
            logger.info(
                "检测到模型配置变更: %s → %s",
                self._config.primary_model, new_config.primary_model,
            )
            self._config = new_config
            self._load_models()

    def get_pool_status(self) -> dict:
        """获取模型池状态摘要（用于 /health 端点）"""
        return {
            "primary": {
                "name": self._primary.name if self._primary else None,
                "status": self._primary.status.value if self._primary else "not_configured",
            },
            "fallbacks": [
                {"name": m.name, "status": m.status.value}
                for m in self._fallbacks
            ],
            "active_model": (
                self.get_active_model().name
                if self.get_active_model()
                else "template_fallback"
            ),
            "template_fallback_enabled": self._config.template_fallback_enabled,
        }
