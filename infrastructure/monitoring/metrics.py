from prometheus_client import Counter, Histogram, Gauge
import time

# Request metrics
request_count = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

request_latency = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint'],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

request_errors = Counter(
    'http_request_errors_total',
    'Total HTTP request errors',
    ['method', 'endpoint', 'error_type']
)

# LLM-specific metrics
tokens_used = Counter(
    'llm_tokens_used_total',
    'Total tokens used in LLM requests',
    ['model', 'token_type']
)

request_cost = Counter(
    'llm_request_cost_total',
    'Total cost of LLM requests in USD',
    ['model']
)

tokens_per_request = Histogram(
    'llm_tokens_per_request',
    'Number of tokens per LLM request',
    ['model'],
    buckets=(10, 50, 100, 500, 1000, 5000, 10000)
)

cost_per_request = Histogram(
    'llm_cost_per_request',
    'Cost of LLM request in USD',
    ['model'],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.05, 0.1)
)

# Active requests gauge
active_requests = Gauge(
    'http_requests_active',
    'Active HTTP requests',
    ['method', 'endpoint']
)

# Resource metrics (useful for monitoring)
llm_response_latency = Histogram(
    'llm_response_duration_seconds',
    'LLM response latency in seconds',
    ['model'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0)
)
