"""
OpenTelemetry setup → Grafana Cloud OTLP export.
Called once at startup. Silently skipped if OTEL_ENABLED != 'true' or packages missing.
"""
import os
import logging

# Enable debug logging if requested
if os.getenv("OTEL_LOG_LEVEL", "").lower() == "debug":
    logging.basicConfig(level=logging.DEBUG)


def setup_telemetry(app=None) -> None:
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

        # Parse "Key=Value" (single pair — Grafana uses one header)
        headers: dict[str, str] = {}
        for part in headers_raw.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                headers[k.strip()] = v.strip()

        resource = Resource(attributes={SERVICE_NAME: service_name})
        provider = TracerProvider(resource=resource)

        # Use BatchSpanProcessor with explicit flush interval (5 seconds)
        exporter = OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
            headers=headers,
            timeout=10,  # 10 second timeout for sending
        )
        span_processor = BatchSpanProcessor(
            exporter,
            schedule_delay_millis=5000,  # Flush every 5 seconds
            max_queue_size=2048,
            max_export_batch_size=512,
        )
        provider.add_span_processor(span_processor)
        trace.set_tracer_provider(provider)

        # Instrument FastAPI routes (adds span per request)
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)

        # Instrument outgoing HTTP calls and DB queries
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

        print(f"✅ OpenTelemetry → Grafana Cloud")
        print(f"   Service: {service_name}")
        print(f"   Endpoint: {endpoint}/v1/traces")
        print(f"   Flush interval: 5s")

    except ImportError as e:
        print(f"⚠️  OpenTelemetry packages missing, skipping tracing: {e}")
    except Exception as e:
        print(f"⚠️  OpenTelemetry setup error, skipping tracing: {e}")
