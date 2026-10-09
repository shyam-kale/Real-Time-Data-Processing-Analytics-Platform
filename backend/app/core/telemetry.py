"""
OpenTelemetry setup → Grafana Cloud OTLP export.
Called once at startup. Silently skipped if OTEL_ENABLED != 'true' or packages missing.
"""
import os


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

        exporter = OTLPSpanExporter(
            endpoint=f"{endpoint}/v1/traces",
            headers=headers,
        )
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        # Instrument FastAPI routes (adds span per request)
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)

        # Instrument outgoing HTTP calls and DB queries
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

        print(f"✅ OpenTelemetry enabled → Grafana (service={service_name}, endpoint={endpoint})")

    except ImportError as e:
        print(f"⚠️  OpenTelemetry packages missing, skipping tracing: {e}")
    except Exception as e:
        print(f"⚠️  OpenTelemetry setup error, skipping tracing: {e}")
