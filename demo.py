"""
Grafana OTLP connection test — run this locally to verify traces reach Grafana.

Usage:
    pip install opentelemetry-sdk opentelemetry-exporter-otlp-proto-http
    python demo.py
"""
import time
import os
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

ENDPOINT = "https://otlp-gateway-prod-ap-south-1.grafana.net/otlp"
TOKEN    = "MTU5NTMwMzpnbGNfZXlKdklqb2lNVGN6TWpJME1TSXNJbTRpT2lKeVpXRnNMWFJwYldVdGNISnZZMlZ6YzJsdVp5SXNJbXNpT2lJeVNubFdOR1JxYkRONFR6aFVSMEk0TjFVMU5WRXlPSE1pTENKdElqcDdJbklpT2lKd2NtOWtMV0Z3TFhOdmRYUm9MVEVpZlgwPQ=="

provider = TracerProvider(
    resource=Resource.create({"service.name": "real-time-processing"})
)
provider.add_span_processor(
    BatchSpanProcessor(
        OTLPSpanExporter(
            endpoint=f"{ENDPOINT}/v1/traces",
            headers={"Authorization": f"Basic {TOKEN}"},
        )
    )
)
trace.set_tracer_provider(provider)

tracer = trace.get_tracer(__name__)

print("Sending test spans to Grafana Cloud...")

with tracer.start_as_current_span("connection-test") as span:
    span.set_attribute("test", True)
    span.set_attribute("app", "dataflow")
    time.sleep(0.5)

    with tracer.start_as_current_span("db-query-simulation"):
        time.sleep(0.2)

    with tracer.start_as_current_span("api-response"):
        time.sleep(0.1)

# Force flush — sends all buffered spans immediately before script exits
provider.force_flush()
provider.shutdown()

print("✅ Traces flushed to Grafana Cloud!")
print("   Go to Grafana → Explore → Tempo to see them.")
