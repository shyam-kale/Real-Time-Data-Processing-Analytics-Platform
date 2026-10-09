"""
Grafana OTLP connection test — sends both traces AND metrics.
Run this locally to verify data reaches Grafana.

Usage:
    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
    python demo.py
"""
import time
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

ENDPOINT = "https://otlp-gateway-prod-ap-south-1.grafana.net/otlp"
TOKEN    = "MTU5NTMwMzpnbGNfZXlKdklqb2lNVGN6TWpJME1TSXNJbTRpT2lKeVpXRnNMWFJwYldVdGNISnZZMlZ6YzJsdVp5SXNJbXNpT2lJeVNubFdOR1JxYkRONFR6aFVSMEk0TjFVMU5WRXlPSE1pTENKdElqcDdJbklpT2lKd2NtOWtMV0Z3TFhOdmRYUm9MVEVpZlgwPQ=="
HEADERS  = {"Authorization": f"Basic {TOKEN}"}
RESOURCE = Resource.create({"service.name": "real-time-processing"})

# ── Traces ────────────────────────────────────────────────────────────────────
trace_provider = TracerProvider(resource=RESOURCE)
trace_provider.add_span_processor(
    BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{ENDPOINT}/v1/traces", headers=HEADERS))
)
trace.set_tracer_provider(trace_provider)

# ── Metrics ───────────────────────────────────────────────────────────────────
metric_reader = PeriodicExportingMetricReader(
    OTLPMetricExporter(endpoint=f"{ENDPOINT}/v1/metrics", headers=HEADERS),
    export_interval_millis=1000,  # export every 1 second
)
meter_provider = MeterProvider(resource=RESOURCE, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

# ── Generate traces ───────────────────────────────────────────────────────────
tracer = trace.get_tracer(__name__)
print("Sending traces to Grafana Cloud...")
with tracer.start_as_current_span("connection-test") as span:
    span.set_attribute("app", "dataflow")
    span.set_attribute("environment", "production")
    time.sleep(0.3)
    with tracer.start_as_current_span("db-query-simulation"):
        time.sleep(0.2)
    with tracer.start_as_current_span("api-response"):
        time.sleep(0.1)

# ── Generate metrics ──────────────────────────────────────────────────────────
print("Sending metrics to Grafana Cloud...")
meter = metrics.get_meter(__name__)

requests_counter = meter.create_counter(
    "app_requests_total",
    description="Total number of API requests",
)
dataset_counter = meter.create_counter(
    "app_datasets_processed",
    description="Total datasets processed",
)
latency_histogram = meter.create_histogram(
    "app_request_duration_ms",
    description="API request duration in milliseconds",
)

# Record some sample metrics
requests_counter.add(10, {"environment": "production", "endpoint": "/api/v1/datasets"})
requests_counter.add(5,  {"environment": "production", "endpoint": "/api/v1/analytics"})
requests_counter.add(3,  {"environment": "production", "endpoint": "/api/v1/pipelines"})
dataset_counter.add(5,   {"environment": "production"})
latency_histogram.record(42.3,  {"endpoint": "/api/v1/datasets"})
latency_histogram.record(120.5, {"endpoint": "/api/v1/analytics"})
latency_histogram.record(18.2,  {"endpoint": "/health"})

# Wait for periodic export to fire
time.sleep(2)

# Force flush everything before exit
trace_provider.force_flush()
trace_provider.shutdown()
meter_provider.force_flush()
meter_provider.shutdown()

print("✅ Traces + Metrics flushed to Grafana Cloud!")
print("   Traces  → Grafana Explore → Tempo")
print("   Metrics → Grafana Explore → Prometheus → query: {__name__=~\".+\"}")
