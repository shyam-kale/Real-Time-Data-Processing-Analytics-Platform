"""
OpenTelemetry setup → Grafana Cloud OTLP export.
Called once at startup. Silently skipped if OTEL_ENABLED != 'true' or packages missing.
"""
import os
import logging

if os.getenv("OTEL_LOG_LEVEL", "").lower() == "debug":
    logging.basicConfig(level=logging.DEBUG)

# Module-level provider reference so lifespan can call force_flush + shutdown
_provider = None


def setup_telemetry(app=None) -> None:
    global _provider

    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        service_name = os.getenv("OTEL_SERVICE_NAME", "dataflow")
        endpoint     = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
        headers_raw  = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

        # Parse "Authorization=Basic <token>" correctly
        # The value may contain "=" characters (base64), so split on first "=" only
        headers: dict[str, str] = {}
        for part in headers_raw.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                headers[k.strip()] = v.strip()

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        exporter = OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
            headers=headers,
            timeout=10,
        )
        processor = BatchSpanProcessor(
            exporter,
            schedule_delay_millis=5000,   # flush every 5s
            max_queue_size=2048,
            max_export_batch_size=512,
        )
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        _provider = provider

        # Send a startup span immediately so Grafana receives data right away
        tracer = trace.get_tracer("dataflow.startup")
        with tracer.start_as_current_span("app.startup"):
            pass
        provider.force_flush()  # flush the startup span before uvicorn is ready

        # Auto-instrument FastAPI, SQLAlchemy, httpx
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

        print(f"✅ OpenTelemetry → Grafana Cloud")
        print(f"   Service : {service_name}")
        print(f"   Endpoint: {endpoint}/v1/traces")

    except ImportError as e:
        print(f"⚠️  OpenTelemetry packages missing, skipping: {e}")
    except Exception as e:
        print(f"⚠️  OpenTelemetry setup error, skipping: {e}")


def shutdown_telemetry() -> None:
    """Call at app shutdown to flush remaining spans before process exits."""
    global _provider
    if _provider is None:
        return
    try:
        _provider.force_flush()
        _provider.shutdown()
        print("✅ OpenTelemetry flushed and shut down")
    except Exception as e:
        print(f"⚠️  OpenTelemetry shutdown error: {e}")
