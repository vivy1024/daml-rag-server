"""OpenTelemetry 全链路追踪集成"""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor


def init_tracing(service_name: str = "daml-rag-server"):
    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    return provider


def get_tracer(name: str = __name__) -> trace.Tracer:
    return trace.get_tracer(name)


def instrument_fastapi(app):
    FastAPIInstrumentor.instrument_app(app)
