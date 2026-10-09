"""
OpenTelemetry setup → Grafana Cloud OTLP export (traces + metrics).
Called once at startup. Silently skipped if OTEL_ENABLED != 'true' or packages missing.
"""
import os
import logging

if os.getenv("OTEL_LOG_LEVEL", "").lower() == "debug":
    logging.basicConfig(level=logging.DEBUG)

_provider       = None  # TracerProvider
_meter_provider = None  # MeterProvider


def setup_telemetry(app=None) -> None:
    global _provider, _meter_provider

    if os.getenv("OTEL_ENABLED", "false").lower() != "true":
        return

    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource, SERVICE_NAME
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        service_name = os.getenv("OTEL_SERVICE_NAME", "dataflow")
        endpoint     = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").rstrip("/")
        headers_raw  = os.getenv("OTEL_EXPORTER_OTLP_HEADERS", "")

        # Parse "Authorization=Basic <token>"
        headers: dict[str, str] = {}
        for part in headers_raw.split(","):
            if "=" in part:
                k, v = part.split("=", 1)
                headers[k.strip()] = v.strip()

        resource = Resource(attributes={SERVICE_NAME: service_name})

        # ── Traces ────────────────────────────────────────────────────────────
        trace_provider = TracerProvider(resource=resource)
        trace_provider.add_span_processor(BatchSpanProcessor(
            OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces", headers=headers, timeout=10),
            schedule_delay_millis=5000,
            max_queue_size=2048,
            max_export_batch_size=512,
        ))
        trace.set_tracer_provider(trace_provider)
        _provider = trace_provider

        # ── Metrics ───────────────────────────────────────────────────────────
        metric_reader = PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics", headers=headers, timeout=10),
            export_interval_millis=15000,  # export every 15s
        )
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        _meter_provider = meter_provider

        # Register app-level metrics
        meter = metrics.get_meter("dataflow")
        _request_counter  = meter.create_counter("app_requests_total",      description="Total API requests")
        _dataset_counter  = meter.create_counter("app_datasets_processed",  description="Datasets processed")
        _pipeline_counter = meter.create_counter("app_pipelines_run",       description="Pipeline runs triggered")
        _latency          = meter.create_histogram("app_request_duration_ms", description="Request duration ms")

        # ── Auto-instrument ───────────────────────────────────────────────────
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
        HTTPXClientInstrumentor().instrument()
        SQLAlchemyInstrumentor().instrument()

        # Send startup span + flush immediately so Grafana gets data on boot
        tracer = trace.get_tracer("dataflow.startup")
        with tracer.start_as_current_span("app.startup"):
            _request_counter.add(1, {"endpoint": "startup", "environment": "production"})
        trace_provider.force_flush()
        meter_provider.force_flush()

        print(f"✅ OpenTelemetry → Grafana Cloud")
        print(f"   Service : {service_name}")
        print(f"   Traces  : {endpoint}/v1/traces")
        print(f"   Metrics : {endpoint}/v1/metrics")

    except ImportError as e:
        print(f"⚠️  OpenTelemetry packages missing, skipping: {e}")
    except Exception as e:
        print(f"⚠️  OpenTelemetry setup error, skipping: {e}")


def shutdown_telemetry() -> None:
    """Flush all pending spans and metrics before process exits."""
    global _provider, _meter_provider
    try:
        if _provider:
            _provider.force_flush()
            _provider.shutdown()
        if _meter_provider:
            _meter_provider.force_flush()
            _meter_provider.shutdown()
        print("✅ OpenTelemetry flushed and shut down")
    except Exception as e:
        print(f"⚠️  OpenTelemetry shutdown error: {e}")
