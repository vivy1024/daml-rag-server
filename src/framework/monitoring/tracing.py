"""OpenTelemetry 全链路追踪集成

OTEL_TRACING_ENABLED=true 启用（默认关闭），生产环境不会输出 span。
"""
import os
import logging

from opentelemetry import trace

logger = logging.getLogger(__name__)

_TRACING_ENABLED = os.getenv("OTEL_TRACING_ENABLED", "false").lower() == "true"


def init_tracing(service_name: str = "daml-rag-server"):
    if not _TRACING_ENABLED:
        return None
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.resources import Resource

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry 追踪已启用 (ConsoleSpanExporter)")
    return provider


def get_tracer(name: str = __name__) -> trace.Tracer:
    return trace.get_tracer(name)


def instrument_fastapi(app):
    if not _TRACING_ENABLED:
        return
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)
