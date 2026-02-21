# -*- coding: utf-8 -*-
"""
DAML-RAG API Server

统一的API服务器入口点，集成：
- 三层检索架构
- 字段标准化
- 反幻觉验证
- 性能监控
- 错误处理

版本：v2.0.0
更新日期：2025-11-17
重构说明：适配三层检索架构，提供生产级API服务
"""

import logging
import asyncio
import os
import sys
import time
import json
from datetime import datetime
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

# 添加src目录到Python路径
if __name__ == "__main__":
    src_path = Path(__file__).parent.parent
    if str(src_path) not in sys.path:
        sys.path.insert(0, str(src_path))

# 导入路由
from .routes import api_router
from .models import ApiResponse, ApiError

# 导入框架核心（v3.0使用simple_framework_initializer）
from src.framework.core.simple_framework_initializer import initialize_framework, get_framework_initializer

# 自定义JSON编码器处理datetime对象
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# 导入应用层适配器 (已废弃 - adapters目录在v2.13.3冗余组件清理中被删除)
# from ..applications.fitness.adapters.user_profile_provider import create_user_profile_provider

# 配置日志
from .config.logging_config import configure_logging
configure_logging()
logger = logging.getLogger(__name__)

# 全局配置
VERSION = "2.0.0"
START_TIME = time.time()


class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime对象"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.warning("🚀 DAML-RAG API Server 启动中...")  # 使用WARNING确保显示

    try:
        # ✅ 初始化Prometheus指标
        try:
            from src.framework.monitoring.prometheus_integration import initialize_prometheus_metrics
            initialize_prometheus_metrics()
            logger.info("✅ Prometheus指标初始化完成")
        except Exception as e:
            logger.warning(f"⚠️ Prometheus指标初始化失败: {e}，监控功能可能受限")

        # 预加载BGE模型到全局缓存
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("🔄 预加载BGE模型...")
        try:
            from src.framework.models.model_cache_manager import ModelCacheManager
            model_cache = ModelCacheManager.get_instance()
            model_cache.preload_models()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("✅ BGE模型预加载完成")
        except Exception as e:
            logger.warning(f"⚠️ BGE模型预加载失败: {e}，将在首次使用时加载")

        # 创建应用层用户档案提供器 (已废弃 - adapters目录已被删除)
        # user_profile_provider = create_user_profile_provider()
        # logger.info("✅ 用户档案提供器创建成功")

        # 初始化DAML-RAG框架 v3.0（不注入用户档案提供器）
        framework_config = {
            # "user_profile_provider": user_profile_provider  # 已废弃
        }
        init_result = await initialize_framework(framework_config, domain_adapter="fitness")
        if init_result.success:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("✅ DAML-RAG框架v3.0初始化成功")
                logger.debug(f"📊 初始化组件数: {len(init_result.components)}")
        else:
            logger.error(f"❌ DAML-RAG框架初始化失败")
            if init_result.errors:
                for component, error in init_result.errors.items():
                    logger.error(f"  ❌ {component}: {error}")
            # v3.0: 允许部分初始化，不抛出异常
            logger.warning("⚠️ 框架部分初始化，服务将以降级模式运行")

        # ✅ 初始化 Skills 架构（DAG模板管理）
        if init_result.domain_adapter:
            try:
                from src.framework.skills import initialize_skills_from_adapter
                skills_integration = initialize_skills_from_adapter(init_result.domain_adapter)
                sm = skills_integration.get_skill_manager()
                skill_count = sm.get_skill_count() if sm else 0
                logger.info(f"✅ Skills架构初始化完成: {skill_count} 个技能")
            except Exception as e:
                logger.warning(f"⚠️ Skills架构初始化失败: {e}")

        # ✅ 启动预热系统（根据feature flag选择新旧系统）
        try:
            import os
            use_new_cache = os.getenv('USE_NEW_CACHE', 'false').lower() in ('true', '1', 'yes')
            
            if use_new_cache:
                # 使用新预热系统（WarmupManager）
                from src.framework.storage.warmup import (
                    WarmupManager,
                    WarmupConfig,
                    set_warmup_manager
                )
                
                # 创建 BackendClient
                from src.applications.fitness.clients.backend_client import BackendClient
                backend_client = BackendClient()
                
                # 获取实际用户ID列表
                critical_user_ids = []
                try:
                    real_users = await backend_client.get_active_user_ids(limit=20)
                    if real_users:
                        critical_user_ids = real_users
                        logger.info(f"✅ 从后端获取到 {len(critical_user_ids)} 个实际用户ID: {critical_user_ids[:5]}...")
                    else:
                        logger.info("ℹ️ 后端暂无活跃用户，跳过用户预热")
                except Exception as user_fetch_error:
                    logger.warning(f"⚠️ 获取用户ID列表失败: {user_fetch_error}，跳过用户预热")
                
                # 初始化缓存单例
                from src.applications.fitness.workflow.singletons import (
                    get_user_cache,
                    get_membership_cache
                )
                user_cache = get_user_cache(backend_client=backend_client)
                membership_cache = get_membership_cache(backend_client=backend_client)
                
                # 配置新预热系统
                warmup_config = WarmupConfig(
                    enabled=True,
                    batch_size=10,
                    max_concurrent=5,
                    timeout=30
                )
                
                # 创建并启动新预热管理器
                warmup_manager = WarmupManager(
                    config=warmup_config,
                    user_profile_cache=user_cache,
                    membership_cache=membership_cache
                )
                
                # 设置全局单例
                set_warmup_manager(warmup_manager)
                
                # 启动预热（非阻塞）
                await warmup_manager.start()
                
                logger.info("✅ 预热系统（WarmupManager）已启动")
                
                logger.info("✅ 预热系统（WarmupManager）已启动")
            
        except Exception as warmup_error:
            logger.warning(f"⚠️ 预热系统启动失败: {warmup_error}，服务继续运行")

        # 注意：Chat服务已重构
        # Chat路由现在直接调用workflow_executor，不再需要注入ChatService
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("✅ Chat路由已重构为直接调用workflow_executor")

        logger.warning("✅ API Server 启动完成")  # 使用WARNING确保显示
        yield

    except Exception as e:
        logger.error(f"❌ API Server 启动失败: {e}")
        raise

    # 关闭时执行
    logger.warning("🔄 DAML-RAG API Server 关闭中...")

    try:
        # 1. 取消预热任务
        try:
            from src.framework.storage.warmup import get_warmup_manager
            warmup_mgr = get_warmup_manager()
            if warmup_mgr:
                logger.info("✅ 预热系统已停止")
        except Exception as warmup_cancel_error:
            logger.debug(f"⚠️ 预热系统取消失败: {warmup_cancel_error}")

        # 2. 等待进行中的请求完成（最多30秒）
        import asyncio
        try:
            from src.framework.monitoring.concurrency_limiter import concurrency_limiter
            if concurrency_limiter and hasattr(concurrency_limiter, 'active_count') and concurrency_limiter.active_count > 0:
                logger.info(f"⏳ 等待 {concurrency_limiter.active_count} 个进行中的请求完成...")
                for _ in range(30):
                    if concurrency_limiter.active_count == 0:
                        break
                    await asyncio.sleep(1)
                if concurrency_limiter.active_count > 0:
                    logger.warning(f"⚠️ 仍有 {concurrency_limiter.active_count} 个请求未完成，强制关闭")
        except Exception:
            pass

        # 3. 关闭框架资源（连接池、Redis、Neo4j）
        from src.framework.core.simple_framework_initializer import get_framework_initializer
        initializer = get_framework_initializer()
        if initializer:
            await initializer.shutdown()
        logger.info("✅ 框架资源清理完成")

    except Exception as e:
        logger.error(f"❌ 资源清理失败: {e}")

    logger.warning("✅ API Server 已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="DAML-RAG API Server",
    description="""
    ## 三层检索架构API服务

    ### 核心特性
    - **三层检索**: 语义搜索 + 图谱推理 + 业务约束
    - **字段标准化**: 自动数据标准化处理
    - **反幻觉验证**: 三层安全验证机制
    - **个性化回复**: 基于用户档案的定制化
    - **性能监控**: 实时性能指标监控

    ### 主要接口
    - `/api/graphrag/*`: GraphRAG查询接口
    - `/api/v1/chat`: 聊天交互接口
    - `/api/feedback/*`: 用户反馈接口
    - `/api/health/*`: 系统健康检查

    ### 技术架构
    - 框架: FastAPI + asyncio
    - 检索: 三层检索架构
    - 数据库: Neo4j + Qdrant + MySQL + Redis
    - AI模型: DeepSeek + BGE-M3
    """,
    version=VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    default_encoder=CustomJSONEncoder
)

# CORS白名单配置
_DEFAULT_CORS_ORIGINS = [
    "https://yuzhen.fit",
    "https://www.yuzhen.fit",
    "https://api.yuzhen.fit",
    "http://localhost:5173",   # Vite dev server
    "http://localhost:3000",   # 备用本地开发
    "http://127.0.0.1:5173",
]
_extra_origins = os.getenv("CORS_EXTRA_ORIGINS", "")
_cors_origins = _DEFAULT_CORS_ORIGINS + [
    o.strip() for o in _extra_origins.split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Internal-Token", "X-Request-ID"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 添加分布式追踪中间件（trace_id）
try:
    from .middleware.tracing import TracingMiddleware
    app.add_middleware(TracingMiddleware)
    logger.info("✅ 分布式追踪中间件已启用")
except ImportError as e:
    logger.warning(f"⚠️ 追踪中间件加载失败: {e}")

# 添加安全中间件
try:
    from .middleware.security import SecurityMiddleware
    
    # 从环境变量读取安全配置
    enable_rate_limit = os.getenv("ENABLE_RATE_LIMIT", "true").lower() == "true"
    enable_auth = os.getenv("ENABLE_AUTH", "true").lower() == "true"
    enable_input_validation = os.getenv("ENABLE_INPUT_VALIDATION", "true").lower() == "true"
    
    app.add_middleware(
        SecurityMiddleware,
        enable_rate_limit=enable_rate_limit,
        enable_auth=enable_auth,
        enable_input_validation=enable_input_validation
    )
    
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(
            f"✅ 安全中间件已启用: "
            f"rate_limit={enable_rate_limit}, "
            f"auth={enable_auth}, "
            f"input_validation={enable_input_validation}"
        )
except ImportError as e:
    logger.warning(f"⚠️ 安全中间件加载失败: {e}")

# 添加双认证中间件（Internal JWT + X-Internal-Token）
try:
    from .middleware.auth_middleware import DualAuthMiddleware
    from ..framework.auth.internal_jwt_verifier import InternalJwtVerifier

    jwt_secret = os.getenv("INTERNAL_JWT_SECRET", "")
    jwt_issuer = os.getenv("INTERNAL_JWT_ISSUER", "yuzhen-auth-gateway")
    legacy_auth_enabled = os.getenv("LEGACY_AUTH_ENABLED", "true").lower() == "true"

    jwt_verifier = InternalJwtVerifier(jwt_secret, jwt_issuer) if jwt_secret else None

    app.add_middleware(
        DualAuthMiddleware,
        jwt_verifier=jwt_verifier,
        legacy_auth_enabled=legacy_auth_enabled,
    )

    logger.info(
        f"✅ 双认证中间件已启用: "
        f"jwt={'有密钥' if jwt_secret else '无密钥'}, "
        f"legacy_auth={legacy_auth_enabled}"
    )
except ImportError as e:
    logger.warning(f"⚠️ 双认证中间件加载失败: {e}")


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(round(process_time, 4))
    response.headers["X-Server-Version"] = VERSION
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """请求日志中间件（只在DEBUG模式或错误时记录）+ Prometheus指标"""
    start_time = time.time()

    # 只在DEBUG模式记录请求开始
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f"📨 {request.method} {request.url.path} - 开始处理")

    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # ✅ 记录Prometheus指标
        try:
            from src.framework.monitoring.prometheus_integration import record_http_request, request_duration
            
            # 记录HTTP请求状态码
            record_http_request(response.status_code)
            
            # 记录请求耗时（排除健康检查等高频低价值请求）
            if not request.url.path.startswith("/health") and not request.url.path.startswith("/api/health"):
                request_duration.labels(
                    endpoint=request.url.path,
                    method=request.method
                ).observe(process_time)
        except Exception as metric_error:
            # 指标记录失败不影响主业务
            pass

        # 只在DEBUG模式记录成功请求
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                f"✅ {request.method} {request.url.path} - "
                f"状态码: {response.status_code}, "
                f"耗时: {process_time:.3f}s"
            )

        return response

    except Exception as e:
        # 错误时始终记录
        process_time = time.time() - start_time
        
        # ✅ 记录错误指标
        try:
            from src.framework.monitoring.prometheus_integration import record_error
            record_error("exception", "api")
        except (ImportError, AttributeError):
            pass
        
        logger.error(
            f"❌ {request.method} {request.url.path} - "
            f"错误: {str(e)}, "
            f"耗时: {process_time:.3f}s"
        )
        raise


# 全局异常处理器
@app.exception_handler(ApiError)
async def api_error_handler(request: Request, exc: ApiError):
    """处理API错误异常"""
    response_data = ApiResponse.error(
        code=exc.code,
        msg=exc.msg,
        data=exc.data
    )

    return JSONResponse(
        status_code=200,  # API错误也返回200，通过code区分
        content=response_data.model_dump(exclude_none=True)
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """处理HTTP异常"""
    response_data = ApiResponse.error(
        code=exc.status_code,
        msg=exc.detail,
        data=None
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=json.loads(response_data.model_dump_json(exclude_none=True, encoder=CustomJSONEncoder)),
        media_type="application/json"
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理通用异常"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    
    # ✅ 记录错误到Prometheus
    try:
        from src.framework.monitoring.prometheus_integration import record_error
        error_type = type(exc).__name__
        record_error(error_type, "api")
    except (ImportError, AttributeError):
        pass

    # 使用自定义JSON编码器处理datetime对象
    response_data = ApiResponse.error(
        code=500,
        msg="服务器内部错误",
        data={"error": str(exc)} if os.getenv("DEBUG") else None
    )

    return JSONResponse(
        status_code=500,
        content=json.loads(response_data.model_dump_json(exclude_none=True))
    )


# 根路径
@app.get("/", response_model=ApiResponse[dict])
async def root():
    """
    API根路径

    返回API服务基本信息和状态
    """
    return ApiResponse.success(
        data={
            "service": "DAML-RAG API Server",
            "version": VERSION,
            "status": "running",
            "uptime_seconds": int(time.time() - START_TIME),
            "documentation": "/docs",
            "health_check": "/api/health"
        },
        msg="DAML-RAG API 服务运行正常"
    )


@app.get("/version", response_model=ApiResponse[dict])
async def version_info():
    """
    版本信息接口

    返回详细的版本信息
    """
    return ApiResponse.success(
        data={
            "api_version": VERSION,
            "framework_version": "4.0.0",
            "three_layer_retrieval": "v4.0.0",
            "field_standardization": "v1.0.0",
            "anti_hallucination": "v3.0.0",
            "build_date": "2025-11-17",
            "environment": os.getenv("ENVIRONMENT", "development")
        },
        msg="版本信息获取成功"
    )


# 包含API路由
app.include_router(api_router, prefix="/api")


# 健康检查（兼容性）
@app.get("/health", response_model=ApiResponse[dict])
async def simple_health():
    """
    简单健康检查（兼容性接口）

    提供基本的健康状态信息
    """
    try:
        # 简化的健康检查
        from src.framework.core.simple_framework_initializer import get_framework_initializer
        initializer = get_framework_initializer()
        framework_healthy = initializer is not None

        return ApiResponse.success(
            data={
                "status": "healthy" if framework_healthy else "degraded",
                "api_server": "healthy",
                "framework": framework_healthy,
                "version": VERSION,
                "uptime": int(time.time() - START_TIME),
                "components": {
                    "framework_initializer": framework_healthy,
                    "api_server": True
                }
            },
            msg="服务健康"
        )

    except Exception as e:
        return ApiResponse.error(
            code=500,
            msg="健康检查失败",
            data={"error": str(e)}
        )


# 开发环境专用路由
if os.getenv("ENVIRONMENT") == "development":
    @app.get("/debug/routes")
    async def debug_routes():
        """调试：显示所有路由"""
        routes = []
        for route in app.routes:
            if hasattr(route, 'methods') and hasattr(route, 'path'):
                routes.append({
                    "methods": list(route.methods),
                    "path": route.path,
                    "name": route.name
                })
        return {"routes": routes}

    @app.get("/debug/config")
    async def debug_config():
        """调试：显示环境配置"""
        import os
        config = {
            "ENVIRONMENT": os.getenv("ENVIRONMENT", "development"),
            "DEBUG": os.getenv("DEBUG", "false"),
            "NEO4J_URI": os.getenv("NEO4J_URI", "not_set"),
            "QDRANT_HOST": os.getenv("QDRANT_HOST", "not_set"),
            "QDRANT_PORT": os.getenv("QDRANT_PORT", "not_set"),
        }
        return {"config": config}


def create_app():
    """创建FastAPI应用的工厂函数"""
    return app


# 如果直接运行此文件
if __name__ == "__main__":
    import uvicorn

    # 从环境变量读取配置
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    reload = os.getenv("ENVIRONMENT") == "development"

    logger.info(f"🚀 启动DAML-RAG API Server: http://{host}:{port}")

    uvicorn.run(
        app,  # 直接传递app对象
        host=host,
        port=port,
        reload=reload,
        log_level="info"
    )