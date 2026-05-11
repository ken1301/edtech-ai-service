# Monitoring Setup

This guide explains how to set up, run, and query the monitoring infrastructure for Socratic AI.

## Architecture

```
FastAPI/Flask App
    ↓
    ├── structlog ─────────────→ stdout (JSON logs)
    │                                ↓
    │                          Promtail (reads log)
    │                                ↓
    │                            Loki (stores log)
    │                                ↓
    │                         Grafana (view logs)
    │
    └── prometheus_client ────→ /metrics endpoint
                                   ↓
                            Prometheus (scrape every 15s)
                                   ↓
                            Grafana (view metrics + alerts)
```

## Metrics Collected

### HTTP Request Metrics
1. **Request Latency** (`http_request_duration_seconds`) - Request duration in seconds
2. **Error Rates** (`http_request_errors_total`) - Count of failed requests
3. **Throughput** (`http_requests_total`) - Total requests per second
4. **Active Requests** (`http_requests_active`) - Currently processing requests

### LLM-Specific Metrics
1. **Token Usage** (`llm_tokens_used_total`) - Total tokens used (input + output)
2. **Token Per Request** (`llm_tokens_per_request`) - Distribution of tokens per request
3. **Cost Per Request** (`llm_request_cost_total`) - Total cost in USD
4. **Cost Per Request** (`llm_cost_per_request`) - Distribution of cost per request
5. **LLM Response Latency** (`llm_response_duration_seconds`) - LLM response time

## Getting Started

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Start the Monitoring Stack
```bash
docker-compose up -d
```

This will start:
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Loki**: http://localhost:3100
- **Your API**: http://localhost:8000

### 3. Access Grafana Dashboard
- Go to http://localhost:3000
- Login: `admin` / `admin`
- Navigate to "Dashboards" → "Socratic AI Monitoring"

## Example Queries

### Prometheus Queries

#### Request Throughput
```promql
rate(http_requests_total[1m])
```

#### Error Rate (%)
```promql
(rate(http_request_errors_total[5m]) / rate(http_requests_total[5m])) * 100
```

#### Request Latency (p95)
```promql
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

#### Total Tokens Used
```promql
sum(rate(llm_tokens_used_total[1m]))
```

#### Cost Per User (Last Hour)
```promql
sum by (user_id) (increase(llm_request_cost_total[1h]))
```

#### Average Cost Per Request by Model
```promql
sum by (model) (rate(llm_request_cost_total[5m])) / sum by (model) (rate(llm_tokens_per_request_count[5m]))
```

### Loki Log Queries

#### View All App Logs
```logql
{job="socratic-ai"}
```

#### Filter by Level (ERROR)
```logql
{job="socratic-ai"} | json | level="ERROR"
```

#### Filter by Request Method
```logql
{job="socratic-ai"} | json | method="POST"
```

#### Find High Latency Requests
```logql
{job="socratic-ai"} | json | latency > 1
```

#### LLM Errors
```logql
{job="socratic-ai"} | json | event="llm_request_failed"
```

## Integration Example

Here's how to track LLM metrics in your code:

```python
from infrastructure.monitoring.llm_metrics import LLMMetricsTracker
import time

# In your chat service
start_time = time.time()

# Make LLM request...
response = llm_client.chat.completions.create(...)

elapsed = time.time() - start_time

# Track metrics
LLMMetricsTracker.track_request(
    user_id=user_id,
    model="gpt-4",
    input_tokens=response.usage.prompt_tokens,
    output_tokens=response.usage.completion_tokens,
    input_cost=input_tokens * 0.00003,  # Example pricing
    output_cost=output_tokens * 0.00006,
    response_time=elapsed
)
```

## Viewing Logs & Metrics

### Grafana Dashboard Features
- **Request Throughput**: Real-time requests per second
- **Request Latency**: p95 and p99 percentiles
- **Error Rate**: Failed requests percentage
- **Tokens Per Second**: LLM token usage rate
- **Cost Per Second**: Real-time cost tracking
- **Recent Logs**: Last logs from the application

### Common Debugging Queries

#### Find Slow Requests
Prometheus:
```promql
http_request_duration_seconds{instance="localhost:8000"} > 1
```

#### Find Error Spikes
Loki:
```logql
{job="socratic-ai"} | json | level="ERROR" | stats count by level
```

#### Check User Token Budget
Prometheus:
```promql
sum by (user_id) (llm_tokens_used_total)
```

## Configuration Files

- **prometheus.yml** - Prometheus scrape config (scrapes /metrics every 15s)
- **loki-config.yml** - Loki storage and ingestion config
- **promtail-config.yml** - Promtail log shipping config (watches app.log)
- **grafana-datasources.yml** - Datasource configuration for Prometheus & Loki
- **grafana-dashboards.yml** - Dashboard provisioning config
- **dashboards/socratic-ai-overview.json** - Pre-built dashboard with key metrics

## Troubleshooting

### Prometheus not scraping metrics
Check: `http://localhost:9090/targets` - ensure the socratic-ai job shows as "UP"

### Loki not receiving logs
1. Check promtail container: `docker logs promtail`
2. Verify app.log is being written
3. Check loki container logs: `docker logs loki`

### Metrics not appearing
1. Ensure structlog is outputting JSON
2. Check that prometheus middleware is added to FastAPI app
3. Visit `http://localhost:8000/metrics` to verify metrics endpoint

### Grafana datasources not connecting
Check datasource URLs point to internal docker network names (e.g., `http://prometheus:9090`)

## Production Considerations

1. **Persistence**: Update volumes in docker-compose to persist monitoring data
2. **Retention**: Adjust Prometheus retention policy in prometheus.yml
3. **Authentication**: Enable Grafana authentication for production
4. **Resource Limits**: Set resource limits for prometheus/loki/grafana containers
5. **Backup**: Regular backup of Grafana dashboards and Prometheus data
